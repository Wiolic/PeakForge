"""Core tests on synthetic spectra (no instrument data in the repo).
Optional: PEAKFORGE_TEST_DATA=<folder with .spe/.vms pairs> also checks SPE == VMS."""
import glob
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from peakforge.core import background, lineshapes  # noqa: E402
from peakforge.core.fit import fit, prepare  # noqa: E402
from peakforge.core.model import Component, Param, RegionModel  # noqa: E402
from peakforge.io import load_file  # noqa: E402
from peakforge.project import Project  # noqa: E402


@pytest.mark.parametrize("shape,kw", [("gaussian", {}), ("lorentzian", {}), ("pvoigt", {"eta": 0.4}),
                                      ("gl", {"m": 0.3}), ("sgl", {"m": 0.3}), ("voigt", {"eta": 0.3}),
                                      ("ds", {"alpha": 0.1, "gamma": 0.3}),
                                      ("la", {"alpha": 1.5, "beta": 2.0, "gw": 0.3})])
def test_unit_area(shape, kw):
    x = np.linspace(0, 200, 400001)
    y = lineshapes.profile(shape, x, 60.0, 1.0, **kw)
    tol = 0.02 if shape in ("lorentzian", "pvoigt", "voigt", "sgl") else 0.005   # Lorentz tails
    assert abs(np.trapezoid(y, x) - 1) < tol


@pytest.mark.parametrize("shape,kw", [("ds", {"alpha": 0.15, "gamma": 0.4}),
                                      ("la", {"alpha": 1.2, "beta": 3.0, "gw": 0.3})])
def test_asymmetric_tail_towards_higher_binding_energy(shape, kw):
    """Metallic (DS / LA) asymmetry must extend to HIGHER BE (lower kinetic energy)."""
    x = np.linspace(40, 80, 40001)
    y = lineshapes.profile(shape, x, 60.0, 0.6, **kw)
    peak = x[np.argmax(y)]
    hi = np.trapezoid(y[x > peak + 2], x[x > peak + 2])
    lo = np.trapezoid(y[x < peak - 2], x[x < peak - 2])
    assert hi > 3 * lo


def _synthetic(seed=1):
    rng = np.random.default_rng(seed)
    x = np.linspace(55, 75, 401)
    true = dict(c1=61.0, c2=62.3, a1=3000.0, a2=1500.0, w=1.1)
    y = np.zeros_like(x)
    for c, a in ((true["c1"], true["a1"]), (true["c2"], true["a2"])):
        y += a * lineshapes.profile("gl", x, c, true["w"], m=0.3)
        y += 0.75 * a * lineshapes.profile("gl", x, c + 2.98, true["w"], m=0.3)
    step = np.cumsum(y[::-1])[::-1]
    y = y + 200 + 300 * (1 - step / step[0])
    y = rng.poisson(y * 5) / 5
    return x, y, true


def _model():
    m = RegionModel(region="Ir 4f", fit_range=(55, 75))
    for n, c in (("A", 60.8), ("B", 62.5)):
        comp = Component(name=n, shape="gl", params=dict(center=Param(c, c - 0.8, c + 0.8),
                                                         fwhm=Param(1.0, 0.4, 2.5), area=Param(1000, 0),
                                                         m=Param(0.3, vary=False)))
        comp.set_doublet(True, 2.98, 0.75)
        m.components.append(comp)
    m.comp("B").params["fwhm"].expr = "A.fwhm"
    return m


def test_fit_recovers_parameters():
    x, y, t = _synthetic()
    m = _model()
    r = fit(m, prepare(x, y, m), n_starts=3)
    assert r.ok
    v = r.values
    assert abs(v["A"]["center"] - t["c1"]) < 0.05
    assert abs(v["B"]["center"] - t["c2"]) < 0.05
    assert abs(v["B"]["fwhm"] - v["A"]["fwhm"]) < 1e-9          # expression link
    frac = t["a1"] / (t["a1"] + t["a2"]) * 100
    assert abs(r.fractions["A"] - frac) < 3
    assert r.rms_pct < 3


def test_shirley_monotonic():
    x, y, _ = _synthetic()
    b = background.compute("shirley", x, y)
    step = b[-1] - b[0]
    assert step > 0
    assert np.min(np.diff(b)) > -0.01 * step          # noise may cause tiny dips only
    assert abs(b[0] - y[x <= x[0] + 0.5].mean()) < 1e-6


def test_model_json_roundtrip():
    m = _model()
    m2 = RegionModel.from_json(m.to_json())
    assert m2.to_json() == m.to_json()
    assert m2.validate() == []


def test_project_csv_roundtrip(tmp_path):
    x, y, _ = _synthetic()
    csv = tmp_path / "s1.csv"
    np.savetxt(csv, np.c_[x, y], delimiter=",", header="Binding energy,Ir 4f", comments="")
    p = Project.create(str(tmp_path / "proj"), "t")
    keys = p.add_file(str(csv))
    assert len(keys) == 1
    p.set_model(keys[0], _model())
    m, r = p.fit(keys[0])
    p2 = Project.open(p.path)
    assert p2.get_model_record(keys[0])["result"]["rms_pct"] == pytest.approx(r.rms_pct)


DATA = os.environ.get("PEAKFORGE_TEST_DATA")


@pytest.mark.skipif(not DATA, reason="set PEAKFORGE_TEST_DATA to a folder with .spe/.vms pairs")
def test_spe_equals_vms():
    pairs = 0
    for spe in glob.glob(os.path.join(DATA, "*.spe")):
        base = os.path.basename(spe)[:-4].lower()
        vms = [v for v in glob.glob(os.path.join(DATA, "*.vms")) if os.path.basename(v)[:-4].lower() == base]
        if not vms:
            continue
        a, b = load_file(spe), load_file(vms[0])
        assert [s.region for s in a] == [s.region for s in b]
        for s, t in zip(a, b):
            assert np.allclose(s.be, t.be, atol=1e-3)
            assert np.allclose(s.cps, t.cps, rtol=1e-5)
        pairs += 1
    assert pairs > 0


def test_ir4f_preset_follows_shifted_spectrum():
    """Ir⁰ found at 61.5 eV after charge correction (real IrTaOx data): the preset must follow without
    pinning Ir⁰ / oxide positions at their bounds (oxides are placed by their shift from Ir⁰)."""
    from peakforge import presets
    from peakforge.spectrum import Spectrum
    rng = np.random.default_rng(3)
    x = np.arange(55, 75, 0.1)
    y = np.zeros_like(x)
    for shape, c, w, a, kw in (("ds", 61.5, 0.55, 20000, dict(alpha=0.12, gamma=0.35)),
                               ("pvoigt", 62.2, 1.2, 15000, dict(eta=0.3)),
                               ("pvoigt", 63.4, 1.2, 3000, dict(eta=0.3))):
        y += a * lineshapes.profile(shape, x, c, w, **kw) + 0.75 * a * lineshapes.profile(shape, x, c + 2.98, w, **kw)
    y = rng.poisson(y + 2000 + 1500 * np.cumsum(y) / np.sum(y)).astype(float)
    sp = Spectrum(region="Ir 4f", be=x, cps=y)
    m = presets.model_from_preset("ir4f_metal_oxide", sp)
    r = fit(m, prepare(sp.be, sp.cps, m), n_starts=4)
    assert not [h for h in r.bound_hits if h.startswith(("Ir0.center", "Ir3.shift", "Ir4.shift"))], r.bound_hits
    assert abs(r.values["Ir0"]["center"] - 61.5) < 0.15
    assert [c.name for c in m.legend_components()][:3] == ["Ir4", "Ir3", "Ir0"]
