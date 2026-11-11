"""Method-review regression tests (phase 0). Each test pins one statement of docs/METHODS.md.
Synthetic data only; references are given next to each test."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from peakforge.core import background, lineshapes, quant  # noqa: E402
from peakforge.core.fit import fit, prepare  # noqa: E402
from peakforge.core.model import BackgroundSpec, Component, Param, RegionModel, eval_expr  # noqa: E402
from peakforge.spectrum import Spectrum  # noqa: E402


# --------------------------------------------------------------------------- Tougaard
def _tougaard_reference(x, y, lo_val, hi_val, B, C, D):
    """Independent direct implementation of bg(x) = ∫_{x'<x} K(x - x') [y(x') - y_lo] dx',
    K(T) = B T / ((C - T²)² + D T²)   (Tougaard, Surf. Interface Anal. 56 (2024) eq. 2; U3),
    rescaled to meet the high-BE end point."""
    dx = x[1] - x[0]
    j = y - lo_val
    bg = np.zeros_like(x)
    for i in range(len(x)):
        T = x[i] - x[: i + 1]
        K = B * T / ((C - T ** 2) ** 2 + D * T ** 2)
        bg[i] = np.sum(K * j[: i + 1]) * dx
    bg *= (hi_val - lo_val) / bg[-1]
    return lo_val + bg


def test_tougaard_default_is_universal_u2():
    """Default cross section must be the universal two-parameter U2(1643): B T/(C+T²)²
    (Tougaard 1989; Tougaard SIA 2024 eq. 1). U3 with D = 4C is algebraically identical."""
    B, C, D = BackgroundSpec().tougaard
    T = np.linspace(0.1, 80, 400)
    u2 = T / (C + T ** 2) ** 2
    u3 = T / ((C - T ** 2) ** 2 + D * T ** 2)
    assert np.allclose(u3 / u3.max(), u2 / u2.max(), rtol=1e-9)
    # U2 maximum is at T = sqrt(C/3) ≈ 23.4 eV
    assert abs(T[np.argmax(u3)] - np.sqrt(C / 3)) < 0.3


def test_tougaard_matches_direct_integral():
    x = np.linspace(60, 100, 401)
    y = 100 + 5000 * lineshapes.profile("gl", x, 70, 1.2, m=0.3)
    y = y + 2000 * (x > 70)
    B, C, D = BackgroundSpec().tougaard
    bg = background.compute("tougaard", x, y, avg=0.0, tougaard=(B, C, D))
    ref = _tougaard_reference(x, y, y[0], y[-1], B, C, D)
    assert np.allclose(bg, ref, rtol=1e-6, atol=1e-6)


def test_tougaard_old_default_migrates():
    """Models saved by 0.1 carry (2866, 1643, 1): a U3 with D=1 that has a near-pole at T≈40 eV."""
    b = BackgroundSpec.from_json({"kind": "tougaard", "tougaard": [2866.0, 1643.0, 1.0]})
    assert b.tougaard == BackgroundSpec().tougaard


def test_tougaard_u3_presets_from_literature():
    """U3 (C, D) for Al, Si, polymer from Tougaard SIA 2024 (citing SIA 25 (1997) 137)."""
    p = background.TOUGAARD_PRESETS
    assert p["U3 Al"][1:] == (230.0, 4.5)
    assert p["U3 Si"][1:] == (325.0, 96.0)
    assert p["U3 polymer"][1:] == (551.0, 436.0)


# --------------------------------------------------------------------------- noise / χ²ᵣ
def _poisson_spectrum(seed, t_acq=0.6, n_bg=300.0):
    """cps spectrum whose counts N = cps·t_acq are Poisson."""
    rng = np.random.default_rng(seed)
    x = np.arange(55, 75, 0.05)
    cps = n_bg + 4000 * lineshapes.profile("gl", x, 61.0, 1.0, m=0.3) \
        + 3000 * lineshapes.profile("gl", x, 63.98, 1.0, m=0.3)
    counts = rng.poisson(cps * t_acq)
    return x, counts / t_acq


def _two_peak_model():
    m = RegionModel(region="X", background=BackgroundSpec(kind="none"))
    for n, c in (("A", 61.0), ("B", 63.98)):
        m.components.append(Component(name=n, shape="gl", params=dict(
            center=Param(c, c - 1, c + 1), fwhm=Param(1.0, 0.3, 3), area=Param(3000, 0),
            m=Param(0.3, vary=False))))
    m.components.append(Component(name="bg", shape="gaussian", params=dict(
        center=Param(65, vary=False), fwhm=Param(1e4, vary=False), area=Param(1e4, 0)), in_total=False))
    return m


@pytest.mark.parametrize("weighting", ["none", "poisson"])
@pytest.mark.parametrize("known_time", [True, False])
def test_chi2_red_is_one_for_correct_model(weighting, known_time):
    """With the true model and pure counting noise χ²ᵣ ≈ 1, whether the acquisition time is known
    (counting statistics) or not (noise estimated from the data), and for both weightings."""
    vals = []
    for seed in range(20):     # the estimated noise level alone scatters ±16 % per 400-point spectrum
        x, y = _poisson_spectrum(seed)
        m = _two_peak_model()
        m.weighting = weighting
        r = fit(m, prepare(x, y, m, acq_time=0.6 if known_time else None), n_starts=1)
        vals.append(r.chi2_red)
    assert abs(np.mean(vals) - 1) < 0.1, vals


def test_spectrum_acq_time():
    s = Spectrum("C 1s", np.arange(5.0), np.ones(5), meta=dict(acq_time=0.6, dwell=0.6, sweeps=3))
    assert s.acq_time() == 0.6
    s2 = Spectrum("C 1s", np.arange(5.0), np.ones(5), meta=dict(format="VAMAS", dwell=0.1, sweeps=4))
    assert s2.acq_time() == pytest.approx(0.4)
    s3 = Spectrum("C 1s", np.arange(5.0), np.ones(5), meta=dict(format="table"))
    assert s3.acq_time() is None


# --------------------------------------------------------------------------- uncertainties
def test_fraction_and_linked_errors_match_scatter():
    """Reported 1σ of the fraction and of an expression-linked parameter must agree with the
    scatter over independent noise realisations (within 30 %).
    Unweighted fit of Poisson data: needs the sandwich covariance."""
    fr, fr_err, cB, cB_err = [], [], [], []
    for seed in range(40):
        x, y = _poisson_spectrum(seed, t_acq=0.2)
        m = _two_peak_model()
        m.comp("B").params["center"] = Param(0.0, expr="A.center + 2.98")
        r = fit(m, prepare(x, y, m, acq_time=0.2), n_starts=1)
        fr.append(r.fractions["A"]); fr_err.append(r.stderr["A.fraction"])
        cB.append(r.values["B"]["center"]); cB_err.append(r.stderr["B.center"])
    for vals, errs in ((fr, fr_err), (cB, cB_err)):
        ratio = np.std(vals) / np.mean(errs)
        assert 0.7 < ratio < 1.3, ratio


# --------------------------------------------------------------------------- expressions
@pytest.mark.parametrize("expr", ["__import__('os').system('echo')", "().__class__.__bases__",
                                  "A.center.__class__", "open('x')", "[1][0]", "lambda: 1", "A.nope"])
def test_eval_expr_rejects_unsafe_or_unknown(expr):
    with pytest.raises((ValueError, KeyError)):
        eval_expr(expr, {"A": {"center": 1.0}})


@pytest.mark.parametrize("expr,val", [("A.center + 1.1", 2.1), ("A.fwhm * 1.0", 0.5),
                                      ("max(A.center, 3) - sqrt(4)", 1.0), ("-A.center**2 / 2", -0.5),
                                      ("pi * 0 + exp(0)", 1.0)])
def test_eval_expr_values(expr, val):
    assert eval_expr(expr, {"A": {"center": 1.0, "fwhm": 0.5}}) == pytest.approx(val)


# --------------------------------------------------------------------------- reported FWHM
def test_apparent_fwhm_reported_for_gl_product():
    """CasaXPS-style GL product: the 'fwhm' parameter is not the measured FWHM for 0 < m < 1."""
    x, y = _poisson_spectrum(0)
    m = _two_peak_model()
    r = fit(m, prepare(x, y, m, acq_time=0.6), n_starts=1)
    row = [rw for rw in r.summary_rows(m) if rw["component"] == "A"][0]
    exp = lineshapes.apparent_fwhm("gl", row["fwhm"], m=0.3)
    assert row["fwhm_apparent"] == pytest.approx(exp, rel=1e-3)
    assert abs(exp - row["fwhm"]) / row["fwhm"] > 0.01


# --------------------------------------------------------------------------- charge reference
def test_c1s_reference_refuses_peak_outside_window():
    """Strongly charged sample (C–C at 290 eV raw): must not silently return a wrong position."""
    x = np.arange(278, 298, 0.1)
    y = 500 + 8000 * lineshapes.profile("gl", x, 290.0, 1.2, m=0.3)
    with pytest.raises(ValueError):
        quant.find_c1s_reference(x, y)


def test_c1s_reference_normal_case():
    x = np.arange(278, 298, 0.1)
    y = 500 + 8000 * lineshapes.profile("gl", x, 285.6, 1.2, m=0.3) \
        + 1500 * lineshapes.profile("gl", x, 287.1, 1.4, m=0.3)
    assert abs(quant.find_c1s_reference(x, y) - 285.6) < 0.05


# --------------------------------------------------------------------------- phase 1 findings
def _au4f_shirley(seed, step, t_acq=1.0, fwhm=1.2, m_true=0.5):
    """Au 4f-like GL doublet on a Shirley-type step, peaks fill ~25 % of the window (typical narrow scan).
    Intensity per eV fixed, so counts per channel scale with the step."""
    rng = np.random.default_rng(seed)
    x = np.arange(79, 95 + 1e-9, step)
    y = 2e6 * step * (lineshapes.profile("gl", x, 84.2, fwhm, m=m_true)
                      + 0.75 * lineshapes.profile("gl", x, 87.87, fwhm, m=m_true))
    cum = np.cumsum(y)
    y = y + 3000 + 0.1 * cum * step
    cps = rng.poisson(y * t_acq) / t_acq
    m = RegionModel(region="Au 4f", fit_range=(79, 95))
    c = Component(name="Au", shape="gl", params=dict(center=Param(84, 83, 85), fwhm=Param(1, 0.3, 3),
                                                     area=Param(1e5, 0), m=Param(0.3, 0, 1)))
    c.set_doublet(True, 3.67, 0.75)
    m.components.append(c)
    return x, cps, m


@pytest.mark.parametrize("kind,avg,hi", [("shirley", 0.5, 1.3), ("shirley", 2.0, 1.3),
                                         ("smart", 0.5, 1.45)])
def test_area_error_includes_background_end_point_noise(kind, avg, hi):
    """The background end points are averages of noisy data; their noise moves the whole background and
    hence the area. Found in phase 1 (SASJ / synthetic): without it the area 1σ was 1.6–2.8× too small.
    Smart: the clip inside the iteration adds a non-linear dependence on interior points that the
    end-point propagation does not cover (~1.2× residual underestimate over 150 seeds; METHODS)."""
    areas, errs = [], []
    for seed in range(40):
        x, y, m = _au4f_shirley(seed, 0.1)
        m.background.kind, m.background.avg = kind, avg
        r = fit(m, prepare(x, y, m, acq_time=1.0), n_starts=1)
        areas.append(r.areas["Au"])
        errs.append(r.stderr["Au.total_area"])
    ratio = np.std(areas, ddof=1) / np.mean(errs)
    assert 0.75 < ratio < hi, ratio


@pytest.mark.parametrize("step,fwhm", [(0.05, 1.2), (0.1, 1.2), (0.1, 0.6), (0.5, 1.2)])
def test_noise_level_unbiased_when_peaks_fill_the_window(step, fwhm):
    """Noise estimate (χ²ᵣ basis for tables, noise-ratio check for counts) must not be inflated by peak
    curvature. The old pre-fit second-difference median gave 2–3× at 0.1 eV and ~50× at 0.5 eV steps."""
    ratios, chis = [], []
    for seed in range(20):
        x, y, m = _au4f_shirley(seed, step, fwhm=fwhm)
        r = fit(m, prepare(x, y, m, acq_time=1.0), n_starts=1)
        ratios.append(r.noise_ratio)
        r2 = fit(m, prepare(x, y, m, acq_time=None), n_starts=1)
        chis.append(r2.chi2_red)
    lo, hi = (0.65, 1.35) if step >= 0.5 else (0.8, 1.25)        # 33 points at 0.5 eV: ±25 % scatter
    assert lo < np.median(ratios) < hi, np.median(ratios)
    if step <= 0.1:
        # at 0.5 eV the 0.5 eV end-point average holds 2 points: its noise (a fixed background offset the
        # peaks cannot absorb) legitimately raises χ²ᵣ to ~1.5 even for the true peak model
        assert 0.8 < np.median(chis) < 1.25, np.median(chis)


@pytest.mark.parametrize("shape,kw", [("gl", dict(m=0.3)), ("sgl", dict(m=0.3)),
                                      ("ds", dict(alpha=0.1, gamma=0.3)),
                                      ("la", dict(alpha=1.5, beta=2.0, gw=0.3))])
def test_profile_is_smooth_in_width(shape, kw):
    """The fit's finite-difference Jacobian (relative step ~1.5e-8) must see the true derivative.
    Phase 1 found the numerical grid's point count jumping with the width: wrong ∂/∂fwhm for 20–45 % of
    widths (up to 5000×), e.g. an SGL fit reporting FWHM ± 7e-8 eV."""
    x = np.linspace(280, 296, 321)
    for w in np.linspace(1.0, 1.3, 121):
        h = 1.5e-8 * w
        d1 = (lineshapes.profile(shape, x, 288, w + h, **kw) - lineshapes.profile(shape, x, 288, w, **kw)) / h
        d2 = (lineshapes.profile(shape, x, 288, w + 1e-4, **kw)
              - lineshapes.profile(shape, x, 288, w - 1e-4, **kw)) / 2e-4
        # GL/SGL are analytic (≈1e-7); DS/LA keep ≤10 % from linear interpolation of their grid
        tol = 1e-5 if shape in ("gl", "sgl") else 0.15
        assert np.max(np.abs(d1 - d2)) < tol * np.max(np.abs(d2)), (w, np.max(np.abs(d1 - d2)) / np.max(np.abs(d2)))


@pytest.mark.parametrize("m", [0.0, 0.3, 0.7, 1.0])
def test_gl_product_area_closed_form(m):
    """∫ exp(−a t²)/(1 + b t²) dt = (π/√b)·erfcx(√(a/b)), a = 4 ln2 (1−m), b = 4m: the GL product is
    normalised exactly (no truncation)."""
    x = np.linspace(-400, 400, 800001)
    y = lineshapes.profile("gl", x, 0.0, 1.0, m=m)
    tail = 0.0 if m < 1 else 1 - 2 / np.pi * np.arctan(2 * 400)       # analytic Lorentz tail outside ±400
    assert abs(np.trapezoid(y, x) - (1 - tail)) < 1e-4


def test_noise_model_for_background_subtracted_table():
    """Zero-centred data with constant noise (background already subtracted, background 'none'):
    the post-fit noise level must keep the constant-variance model chosen from the data. Code review
    of phase 1: the envelope (~1e-60 in the tails) was used as Poisson level → χ²ᵣ ≈ 35, area 1σ ×1e7."""
    chis, areas, errs = [], [], []
    for seed in range(30):
        rng = np.random.default_rng(seed)
        x = np.arange(280, 296, 0.05)
        y = 4000 * lineshapes.profile("gaussian", x, 288, 1.1) + rng.normal(0, 20, len(x))
        m = RegionModel(region="C 1s", background=BackgroundSpec(kind="none"))
        m.components.append(Component(name="P", shape="gaussian", params=dict(
            center=Param(288, 287, 289), fwhm=Param(1, 0.3, 3), area=Param(3000, 0))))
        r = fit(m, prepare(x, y, m), n_starts=1)
        chis.append(r.chi2_red)
        areas.append(r.areas["P"])
        errs.append(r.stderr["P.area"])
    assert 0.85 < np.median(chis) < 1.15, np.median(chis)
    assert 0.7 < np.std(areas, ddof=1) / np.mean(errs) < 1.3


@pytest.mark.parametrize("expr", ["A.center if 1 else 0", "[A.center][0]", "A.center +"])
def test_validate_reports_disallowed_expressions(expr):
    m = _two_peak_model()
    m.components[1].params["center"] = Param(0.0, expr=expr.replace("A.", "A."))
    assert m.validate(), expr


def test_expression_overflow_is_a_value_error():
    with pytest.raises(ValueError):
        eval_expr("10.0 ** 400", {})


def test_c1s_reference_accepts_coarse_step():
    """Survey-like 0.5 eV step: the 'clear peak' check must not mistake peak flanks for noise."""
    rng = np.random.default_rng(0)
    x = np.arange(278, 298, 0.5)
    y = 500 + 8000 * lineshapes.profile("gl", x, 285.6, 1.0, m=0.3) \
        + 2500 * lineshapes.profile("gl", x, 287.0, 1.2, m=0.3)
    y = rng.poisson(y).astype(float)
    assert abs(quant.find_c1s_reference(x, y) - 285.6) < 0.1
