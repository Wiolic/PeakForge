"""Known-answer benchmarks on synthetic spectra (phase 1).

Every reference below is either an analytic formula or an independent implementation (scipy), never the code
under test. Tolerances reviewed in phase 1 (Opus): analytic comparisons use numerical-precision bounds; fit recovery
uses z-scores against the reported 1σ, so a bias or a mis-calibrated error both fail."""
import os
import sys

import numpy as np
import pytest
from scipy.special import voigt_profile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from peakforge.core import background, lineshapes  # noqa: E402
from peakforge.core.fit import fit, prepare  # noqa: E402
from peakforge.core.model import Component, Param, RegionModel  # noqa: E402

LN2 = np.log(2.0)


def _fwhm(x, y):
    idx = np.where(y >= y.max() / 2)[0]
    return x[idx[-1]] - x[idx[0]]


# --------------------------------------------------------------------- line shapes vs closed forms
@pytest.mark.parametrize("m", [0.0, 0.3, 0.7, 1.0])
def test_sgl_is_height_weighted_sum(m):
    """CasaXPS SGL(m) = (1-m)·G + m·L with PEAK-normalised (unit-height) G and L, then area-normalised
    (docs/METHODS.md). Compared in the core region; the numerical profile is truncated far in the tails."""
    x = np.linspace(-30, 30, 60001)
    w = 1.3
    ref = (1 - m) * np.exp(-4 * LN2 * x ** 2 / w ** 2) + m / (1 + 4 * x ** 2 / w ** 2)
    got = lineshapes.profile("sgl", x, 0.0, w, m=m)
    core = np.abs(x) < 6 * w          # profile grid ends at -(8w+1) on the low-BE side
    scale = got[core].max() / ref[core].max()          # area normalisation is a constant factor
    assert np.max(np.abs(got[core] / scale - ref[core])) < 2e-3
    assert abs(_fwhm(x, got) - w) < 2e-3          # grid resolution 1e-3


@pytest.mark.parametrize("eta", [0.0, 0.2, 0.5, 0.9])
def test_voigt_matches_scipy_and_has_requested_fwhm(eta):
    """The Voigt component's `fwhm` is its total FWHM; shape equals scipy's voigt_profile for the implied
    Gaussian/Lorentzian widths (independent evaluation of the same convolution)."""
    x = np.linspace(-20, 20, 40001)
    w = 1.2
    y = lineshapes.profile("voigt", x, 0.0, w, eta=eta)
    assert abs(np.trapezoid(y, x) - 1) < 0.02
    assert abs(_fwhm(x, y) - w) < 0.005 * w          # Olivero approximation is good to ~0.02 %
    fl = eta * w
    # independent: pick sigma so that the Voigt FWHM from scipy equals w, then compare shapes
    from scipy.optimize import brentq

    def total(sig):
        yy = voigt_profile(x, sig, fl / 2)
        return _fwhm(x, yy) - w
    if eta < 0.99:
        sig = brentq(total, 1e-4, w)
        ref = voigt_profile(x, sig, fl / 2)
        assert np.max(np.abs(y - ref)) < 5e-3 * ref.max()


# --------------------------------------------------------------------- Shirley fixed point
def test_shirley_recovers_constructed_background():
    """Build y = peak + B with B the exact Shirley form (B(E) = lo + (hi-lo)·cum. peak area up to E / total).
    That B is the fixed point of the iteration, so compute('shirley') must return it."""
    x = np.linspace(280, 295, 1501)
    peak = 5000 * lineshapes.profile("gl", x, 287.5, 1.0, m=0.3)
    lo, hi = 300.0, 1100.0
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (peak[1:] + peak[:-1]) * np.diff(x))])
    b_true = lo + (hi - lo) * cum / cum[-1]
    y = peak + b_true
    b = background.compute("shirley", x, y, avg=0.0)
    assert np.max(np.abs(b - b_true)) < 2e-3 * (hi - lo)


# --------------------------------------------------------------------- fit recovery
def _single(shape, extra, seed, area=4000.0, fwhm=1.1):
    rng = np.random.default_rng(seed)
    x = np.linspace(273, 303, 601)            # ±15 eV: Lorentzian tails beyond ±8 eV bias the area −1.8 % (METHODS)
    y = area * lineshapes.profile(shape, x, 288.0, fwhm, **extra)
    cum = np.cumsum(y)
    y = y + 300 + 250 * cum / cum[-1]
    y = rng.poisson(y * 4) / 4.0
    m = RegionModel(region="C 1s", fit_range=(273, 303))
    params = dict(center=Param(287.8, 287.0, 289.0), fwhm=Param(1.0, 0.3, 3.0), area=Param(1000, 0))
    for k, v in extra.items():
        params[k] = Param(v, vary=False)
    m.components.append(Component(name="P", shape=shape, params=params))
    return x, y, m


@pytest.mark.parametrize("shape,extra", [("gaussian", {}), ("lorentzian", {}), ("pvoigt", {"eta": 0.3}),
                                         ("gl", {"m": 0.3}), ("sgl", {"m": 0.3}), ("voigt", {"eta": 0.3})])
def test_single_peak_recovery_statistics(shape, extra):
    """20 Poisson realisations, Shirley background computed from the data, true model.
    Tolerances are statistical (z = (fit − true) / reported 1σ), so they test bias AND error calibration:
      |mean z| < 0.9  (σ of the mean of 20 is 0.22 → ≈4σ; a 0.1σ bias would pass, a 1σ bias fail),
      0.6 < sd(z) < 1.5 (sd of 20 samples scatters ±16 %; errors off by >1.5× fail).
    Plus an absolute sanity bound: centre within 0.05 eV in every realisation."""
    z = {"center": [], "fwhm": [], "area": []}
    true = {"center": 288.0, "fwhm": 1.1, "area": 4000.0}
    for seed in range(20):
        x, y, m = _single(shape, extra, seed)
        r = fit(m, prepare(x, y, m, acq_time=4.0), n_starts=2)
        assert r.ok
        v = r.values["P"]
        assert abs(v["center"] - 288.0) < 0.05
        for k in z:
            err = r.stderr["P.total_area" if k == "area" else f"P.{k}"]
            val = r.areas["P"] if k == "area" else v[k]
            z[k].append((val - true[k]) / err)
    for k, zz in z.items():
        assert abs(np.mean(zz)) < 0.9, (k, np.mean(zz))
        assert 0.6 < np.std(zz, ddof=1) < 1.5, (k, np.std(zz, ddof=1))
