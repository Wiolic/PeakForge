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
    r = quant.find_reference(x, y, 284.8)          # found, but not trusted
    assert abs(r.position - 290.0) < 0.05 and r.confidence == "low"


# --------------------------------------------------------------------------- charge reference (phase 3.6 C1)
def _gl(x, c, w, a):
    return a * lineshapes.profile("gl", x, c, w, m=0.3)


def _c1s_like(peaks, step=0.1, lo=278.0, hi=298.0, seed=0, base=3000.0):
    rng = np.random.default_rng(seed)
    x = np.arange(lo, hi, step)
    y = base + sum((_gl(x, c, w, a) for c, w, a in peaks), np.zeros_like(x))
    return x, rng.poisson(y).astype(float)


def test_reference_overcompensated_c1s():
    """PHI neutraliser over-compensation puts raw C–C at ~283 eV (outside the old 283–287 window)."""
    x, y = _c1s_like([(282.9, 1.5, 8000), (284.4, 1.6, 2000)])
    r = quant.find_reference(x, y, 284.8)
    assert abs(r.position - 282.9) < 0.1 and r.confidence == "high"
    assert abs(quant.find_c1s_reference(x, y) - 282.9) < 0.1


def test_reference_ignores_stronger_cf2_k2p_ir4d():
    """CF₂ (+7 eV), K 2p (+8.2/+11 eV) and Ir 4d5/2 (+12.5 eV) above C–C may all be stronger than C–C;
    the reference is the lowest-BE prominent peak, with a local background (no window-wide Shirley)."""
    x, y = _c1s_like([(283.3, 1.4, 3000), (284.8, 1.6, 900), (290.3, 1.5, 9000), (291.5, 1.2, 4000),
                      (294.3, 1.2, 2000), (295.8, 3.5, 30000)])
    r = quant.find_reference(x, y, 284.8)
    assert abs(r.position - 283.3) < 0.1 and r.confidence == "high"
    assert not r.notes
    r = quant.find_reference(x, y, 284.8, fluoro_check=True)    # CF₂ 7.0 eV above C–C
    assert r.confidence == "high" and any("differential charging" in n for n in r.notes)
    x, y = _c1s_like([(283.0, 1.4, 8000), (284.5, 1.6, 2000)])
    assert not quant.find_reference(x, y, 284.8, fluoro_check=True).notes


def test_reference_low_be_shoulder_is_low_confidence():
    """An unresolved component below the chosen maximum means C–C may be the shoulder, not the top."""
    x, y = _c1s_like([(284.5, 1.4, 8000), (283.2, 1.4, 4000)])
    r = quant.find_reference(x, y, 284.8)
    assert r.confidence == "low" and any("shoulder" in s for s in r.reasons)


def test_reference_noise_only_raises():
    x, y = _c1s_like([])
    with pytest.raises(ValueError):
        quant.find_reference(x, y, 284.8)


def test_reference_generic_au4f():
    """Any reference line works the same way: Au 4f7/2 (lowest-BE member of the doublet)."""
    x, y = _c1s_like([(83.1, 0.9, 20000), (86.77, 0.9, 15000)], lo=78, hi=95)
    r = quant.find_reference(x, y, 84.0)
    assert abs(r.position - 83.1) < 0.05 and r.confidence == "high"


def _add(p, tmp_path, name, region, x, y):
    f = tmp_path / f"{name}.csv"
    np.savetxt(f, np.c_[x, y], delimiter=",", header=f"Binding energy,{region}", comments="")
    p.add_file(str(f), sample=name)


def test_project_auto_charge_skips_low_confidence(tmp_path):
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    _add(p, tmp_path, "far", "C 1s", *_c1s_like([(290.0, 1.2, 8000)]))
    _add(p, tmp_path, "ok", "C 1s", *_c1s_like([(283.0, 1.4, 8000)]))
    out = p.auto_charge()
    assert set(out) == {"ok"} and abs(out["ok"] - 1.8) < 0.1
    assert "far" in p.charge_failures and p.shift("far") == 0.0
    out = p.auto_charge(force=True)
    assert abs(out["far"] + 5.2) < 0.1


def test_project_charge_cross_check(tmp_path):
    """Optional internal-consistency checks: a second line of the same sample must land on its expected BE."""
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    _add(p, tmp_path, "s", "C 1s", *_c1s_like([(283.0, 1.4, 8000)]))
    _add(p, tmp_path, "s_o", "O 1s", *_c1s_like([(527.6, 1.1, 9000), (529.6, 1.6, 4000)], lo=524, hi=538))
    p.spectra[p.keys("O 1s")[0]].sample = "s"         # one file per sample in a project; same sample here
    p.settings["charge_checks"] = [dict(region="O 1s", be=529.4, tol=0.3)]
    p.auto_charge()
    assert not p.charge_warnings.get("s")                   # 527.6 + 1.8 = 529.4
    p.settings["charge_checks"] = [dict(region="O 1s", be=530.2, tol=0.3)]
    p.auto_charge()
    assert "O 1s" in p.charge_warnings["s"][0]


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


# --------------------------------------------------------------------------- cancellation hooks (phase 3)
def test_cancel_hooks_do_not_change_results_and_can_abort():
    """fit(check=…) and diagnose(progress=…, check=…) only observe: identical numbers; a raising check aborts."""
    from peakforge.core.diagnostics import diagnose
    from peakforge.tasks import Cancelled, TaskHandle
    x, y = _poisson_spectrum(3)
    m = _two_peak_model()
    prep = prepare(x, y, m, acq_time=0.6)
    calls = []
    a = fit(m, prep, n_starts=2)
    b = fit(m, prep, n_starts=2, check=lambda: calls.append(1))
    assert calls and np.array_equal(a.envelope, b.envelope) and a.stderr == b.stderr and a.bic == b.bic

    seen = []
    d0 = diagnose(m, prep, a, deep=True)
    d1 = diagnose(m, prep, a, deep=True, progress=lambda f, t: seen.append(f), check=lambda: None)
    assert d0["significance"] == d1["significance"] and d0["stability"] == d1["stability"]
    assert seen and seen == sorted(seen) and 0 <= seen[0] and seen[-1] < 1

    h = TaskHandle()
    h.cancel()
    with pytest.raises(Cancelled):
        fit(m, prep, n_starts=1, check=h.check)
    with pytest.raises(Cancelled):
        diagnose(m, prep, a, deep=True, progress=h.progress, check=h.check)


def test_cancelled_is_not_swallowed_by_except_exception():
    from peakforge.tasks import Cancelled, TaskHandle
    h = TaskHandle()
    h.cancel()
    with pytest.raises(Cancelled):
        try:
            h.progress(0.5, "x")
        except Exception:      # noqa: BLE001 — must not catch a cancel
            pytest.fail("Cancelled was caught by except Exception")


def test_project_charge_notes_fluorine_from_survey(tmp_path):
    """C 1s window without CF₂ (ends at 288 eV) but F 1s in the survey: warn about differential charging."""
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    _add(p, tmp_path, "s", "C 1s", *_c1s_like([(283.0, 1.4, 8000)], hi=288))
    _add(p, tmp_path, "s_su", "Survey", *_c1s_like([(283.0, 1.6, 3000), (527.6, 1.6, 9000), (687.0, 2.0, 20000)],
                                                   step=0.5, lo=0, hi=1100))
    p.spectra[p.keys("Survey")[0]].sample = "s"
    p.auto_charge()
    assert "s" in p.auto_charge() and any("F 1s" in w for w in p.charge_warnings["s"])


# --------------------------------------------------------------------------- phase 3.6 C2: low-quality data
def _spec(region, peaks, lo, hi, step=0.1, t=0.2, base=500.0, seed=0):
    """Spectrum with Poisson counts; peaks = [(centre, fwhm, area_cps_eV)] (GL(30))."""
    rng = np.random.default_rng(seed)
    x = np.arange(lo, hi, step)
    y = base + sum((a * lineshapes.profile("gl", x, c, w, m=0.3) for c, w, a in peaks), np.zeros_like(x))
    return Spectrum(region, x, rng.poisson(y * t) / t, sample="s", meta=dict(acq_time=t, format="test"))


def test_resolution_floor():
    from peakforge.core import quality
    assert quality.resolution_floor(np.arange(0, 10, 0.1)) == pytest.approx(0.5)
    assert quality.resolution_floor(np.arange(0, 10, 0.5)) == pytest.approx(1.25)


def test_generic_model_width_floor_follows_sampling():
    from peakforge import presets
    from peakforge.core import quality
    for step in (0.05, 0.25):
        sp = _spec("Ag 3d", [(368.2, 0.9, 4000), (374.2, 0.9, 2667)], 360, 382, step=step)
        m = presets.generic_model(sp)
        floor = quality.resolution_floor(sp.be)
        assert all(c.params["fwhm"].min >= floor - 1e-9 for c in m.components if not c.params["fwhm"].expr)


def test_subshell_label_with_both_partners_is_a_doublet():
    """Instruments name regions after the main line ('Ag 3d5/2', 'Co 2p3/2') even when the window covers
    both spin–orbit partners: the window decides, not the label."""
    from peakforge import presets
    both = _spec("Ag 3d5/2", [(368.2, 0.9, 40000), (374.2, 0.9, 26670)], 360, 382)
    assert presets.covers_partner(both)
    assert all(c.doublet for c in presets.generic_model(both).components)
    one = _spec("Ag 3d5/2", [(368.2, 0.9, 40000)], 364, 372)
    assert not presets.covers_partner(one)
    assert not any(c.doublet for c in presets.generic_model(one).components)


def test_subshell_only_scan_scales_rsf(tmp_path):
    """A scan of one j sub-level holds 1/(1+ratio) (high j) of the level's intensity."""
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    one = _spec("Ag 3d5/2", [(368.2, 0.9, 40000)], 364, 372)
    f = tmp_path / "a.csv"
    np.savetxt(f, np.c_[one.be, one.cps], delimiter=",", header="Binding energy,Ag 3d5/2", comments="")
    k = p.add_file(str(f))[0]
    full = p.rsf("Ag 3d")
    assert p.rsf_for(k) == pytest.approx(full / (1 + 0.6667), rel=1e-3)


def test_low_snr_auto_model_shares_fwhm():
    from peakforge import presets
    sp = _spec("Ag 3d", [(368.2, 1.0, 300), (369.6, 1.0, 150), (374.2, 1.0, 200), (375.6, 1.0, 100)],
               360, 382, t=0.05, base=800)
    m = presets.generic_model(sp)
    assert len(m.components) <= 2
    if len(m.components) == 2:
        assert m.components[1].params["fwhm"].expr == f"{m.components[0].name}.fwhm"


def test_quality_flags_noise_component():
    """A free component where there is no peak ends at zero area or at the width floor: flagged."""
    from peakforge.core import quality
    sp = _spec("X", [(61.0, 1.2, 3000)], 55, 70, t=0.2)
    m = RegionModel(region="X", background=BackgroundSpec(kind="linear"))
    floor = quality.resolution_floor(sp.be)
    for n, c in (("A", 61.0), ("B", 66.0)):
        m.components.append(Component(name=n, shape="gl", params=dict(
            center=Param(c, c - 1, c + 1), fwhm=Param(1.0, floor, 4), area=Param(500, 0), m=Param(0.3, vary=False))))
    r = fit(m, prepare(sp.be, sp.cps, m, acq_time=0.2), n_starts=3)
    codes = {(f["code"], f.get("component")) for f in r.flags}
    assert ("insignificant", "B") in codes or ("narrow", "B") in codes
    assert not any(f.get("component") == "A" for f in r.flags)


def test_quality_reports_width_bound_above_floor():
    """A width stuck at a lower bound ABOVE the resolution floor (e.g. multiplet presets: 0.8 x table width)
    is not covered by the 'narrow' flag and must still be reported as a bound hit."""
    sp = _spec("X", [(61.0, 0.9, 30000)], 55, 70, t=1.0)
    m = RegionModel(region="X", background=BackgroundSpec(kind="linear"))
    m.components.append(Component(name="A", shape="gl", params=dict(
        center=Param(61, 60, 62), fwhm=Param(1.8, 1.5, 4), area=Param(500, 0), m=Param(0.3, vary=False))))
    r = fit(m, prepare(sp.be, sp.cps, m, acq_time=1.0), n_starts=1)
    assert "A.fwhm @min" in r.bound_hits
    assert not any(f["code"] == "narrow" for f in r.flags)
    assert any(f["code"] == "bound" and "A.fwhm @min" in f["text"] for f in r.flags), r.flags


def test_quality_low_snr_and_clean_fit():
    from peakforge.core import quality
    m = RegionModel(region="X", background=BackgroundSpec(kind="linear"))
    m.components.append(Component(name="A", shape="gl", params=dict(
        center=Param(61, 60, 62), fwhm=Param(1.2, 0.5, 4), area=Param(500, 0), m=Param(0.3, vary=False))))
    weak = _spec("X", [(61.0, 1.2, 60)], 55, 70, t=0.2, base=300)
    r = fit(m, prepare(weak.be, weak.cps, m, acq_time=0.2), n_starts=1)
    assert any(f["code"] == "low_snr" for f in r.flags)
    assert quality.peak_snr(r.x, r.y, r.bg) < 30
    strong = _spec("X", [(61.0, 1.2, 30000)], 55, 70, t=1.0, base=300)
    r = fit(m, prepare(strong.be, strong.cps, m, acq_time=1.0), n_starts=1)
    assert not [f for f in r.flags if f["level"] == "error"], r.flags
    assert "flags" in r.to_json(m)


def test_preset_adapted_to_window():
    """Any preset: components beyond the scanned window are removed (noted), free widths respect the
    resolution floor, free centres stay inside the window."""
    from peakforge import presets
    from peakforge.core import quality
    sp = _spec("C 1s", [(284.8, 1.3, 8000), (286.3, 1.3, 1500)], 278.0, 288.0, step=0.25)
    m = presets.model_from_preset("c1s_adventitious", sp)
    a, b = sorted(m.fit_range)
    assert "OCO" not in m.names() and "removed" in m.note
    floor = quality.resolution_floor(sp.be)
    for c in m.components:
        w, ce = c.params["fwhm"], c.params["center"]
        if w.free:
            assert w.min >= floor - 1e-9
        if ce.free:
            assert a < ce.min and ce.max < b


def test_preset_window_removes_chains_of_outside_components():
    """A component referred to only by components that are removed is removed as well."""
    from peakforge import presets
    sp = _spec("X", [(61.0, 1.2, 8000)], 55, 70)
    m = RegionModel(region="X", background=BackgroundSpec(kind="linear"), fit_range=(56.0, 69.0))
    for n, c, expr in (("A", 61.0, None), ("B", 75.0, None), ("C", 78.0, "B.center + 3")):
        m.components.append(Component(name=n, shape="gl", params=dict(
            center=Param(c, c - 1, c + 1, expr=expr), fwhm=Param(1.2, 0.5, 4), area=Param(500, 0),
            m=Param(0.3, vary=False))))
    presets.fit_to_window(m, sp)
    assert m.names() == ["A"]


def test_project_charge_region_override_needs_its_own_ref(tmp_path):
    """--region without --ref must not reuse the energy stored for another reference line."""
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    with pytest.raises(ValueError):
        p.auto_charge(region="Au 4f")
    p.auto_charge(region="Au 4f", ref=84.0)                 # explicit energy: fine
    p.settings["charge_region"], p.settings["charge_ref"] = "Au 4f", 84.0
    assert p.charge_reference("C 1s", None) == 284.8         # C 1s: the usual 284.8 eV, not Au 4f's 84.0
    assert p.charge_reference(None, None) == 84.0


def test_schema_palette_assign_wrong_shape_is_an_error():
    from peakforge import schema
    rep = schema.check_project_data(dict(format="peakforge-project", files=[], samples={},
                                         settings=dict(palette=dict(combo="glacier", assign=["Ir", "azure"]))),
                                    "p.xpsproj")
    assert any("assign" in e for e in rep.errors())


# --------------------------------------------------------------------------- phase 3.6 C3: overlapping lines
def test_overlapping_levels_any_element():
    """Data-driven: every tabulated level of the elements present whose line (or partner, allowing a
    chemical shift of up to +4 eV) falls in the window is reported — no element special cases."""
    from peakforge import presets
    hits = {h["level"] for h in presets.overlapping_levels("Ir 4f", {"Ir", "Co", "O"}, 55.0, 75.0)}
    assert "Co 3p" in hits and "Ir 5p" in hits and "Ir 4f" not in hits
    hits = {h["level"] for h in presets.overlapping_levels("Ta 4f", {"Ta", "O", "F"}, 17.0, 37.0)}
    assert {"O 2s", "F 2s", "Ta 5p"} <= hits
    hits = {h["level"] for h in presets.overlapping_levels("C 1s", {"C", "Ir", "K"}, 278.0, 298.0)}
    assert {"Ir 4d", "K 2p"} <= hits
    assert presets.overlapping_levels("Ir 4f", {"Ir"}, 58.0, 62.0) == []     # Ir 5p1/2 (63.1) outside


def test_project_adds_overlap_flags(tmp_path):
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    _add(p, tmp_path, "s", "Ir 4f", *_c1s_like([(60.9, 0.9, 20000), (63.9, 0.9, 15000)], lo=55, hi=75))
    _add(p, tmp_path, "s_co", "Co 2p", *_c1s_like([(780.0, 2.5, 20000), (795.5, 2.5, 10000)], lo=770, hi=810))
    p.spectra[p.keys("Co 2p")[0]].sample = "s"
    k = p.keys("Ir 4f")[0]
    p.set_model(k, p.new_model(k))
    _m, r = p.fit(k, n_starts=1)
    assert any(f["code"] == "overlap" and "Co 3p" in f["text"] for f in r.flags)
    assert any(f["code"] == "overlap" and "Co 3p" in f["text"] for f in p.evaluate(k).flags)


def _co2p_mixture(seed=1):
    """Co 2p from the Biesinger 2011 Table 5 envelopes: 2/3 Co3O4 + 1/3 Co(OH)2 (2p3/2), a 2p1/2 copy
    (+15.5 eV, half area, 1.2x wider) and an integral (Shirley-type) step."""
    from peakforge import presets
    tab = presets.multiplet_tables()["co2p3_biesinger2011"]["species"]
    x = np.arange(770.0, 812.0, 0.1)
    sig = np.zeros_like(x)
    for spn, tot in (("Co3O4", 30000.0), ("Co(OH)2", 15000.0)):
        for be, a, w in tab[spn]:
            sig += tot * a / 100 * lineshapes.profile("gl", x, be + 0.15, w, m=0.3)
            sig += 0.5 * tot * a / 100 * lineshapes.profile("gl", x, be + 15.65, 1.2 * w, m=0.3)
    y = 600 + sig + 0.02 * np.cumsum(sig) * 0.1
    y = np.random.default_rng(seed).poisson(y * 0.5) / 0.5
    return Spectrum("Co 2p3/2", x, y, sample="s", meta=dict(acq_time=0.5, format="test"))


def _species_fractions(m, r):
    tot = {}
    for c in m.components:
        k = c.name.rsplit("_", 1)[0]
        tot[k] = tot.get(k, 0.0) + r.areas[c.name]
    s = sum(tot.values())
    return {k: v / s for k, v in tot.items()}


def test_multiplet_presets_are_sourced_and_not_automatic():
    """Sourced species envelopes (Biesinger 2011 Table 5, Co 2p3/2) for any 'Co 2p…' label; never the
    automatic default, window ends 1.5 eV below Co 2p1/2, quantification uses the 2p3/2 share."""
    from peakforge import presets
    from peakforge.project import build_model
    sp = _co2p_mixture()
    ids = {p["id"] for p in presets.presets_for("Co 2p3/2")}
    assert "multiplet_co2p3_biesinger2011" in ids and "multiplet_co2p3_biesinger2011:Co3O4" in ids
    assert not build_model(sp, 0.0, ".").preset.startswith("multiplet_")
    m = presets.model_from_preset(presets.multiplet_preset("co2p3_biesinger2011", ["Co3O4", "Co(OH)2"]), sp)
    assert m.region == "Co 2p3/2" and max(m.fit_range) <= 779.6 + 15.0 - 1.5 + 1e-6
    assert presets.high_j_only(m)


def test_multiplet_species_recovered_with_right_species():
    """With the species that are actually present and a linear background, the mixture is recovered
    (2/3 : 1/3 within 0.08). Shirley with the end point on satellite / 2p1/2 intensity biases it
    (METHODS §6c), and all five species at once are not identifiable: flagged as not significant."""
    from peakforge import presets
    sp = _co2p_mixture()
    m = presets.model_from_preset(presets.multiplet_preset("co2p3_biesinger2011", ["Co3O4", "Co(OH)2"]), sp)
    m.background.kind = "linear"
    r = fit(m, prepare(sp.be, sp.cps, m, acq_time=0.5), n_starts=5)
    f = _species_fractions(m, r)
    assert f["Co3O4"] == pytest.approx(2 / 3, abs=0.08) and f["CoOH2"] == pytest.approx(1 / 3, abs=0.08)
    m_all = presets.model_from_preset(presets.multiplet_preset("co2p3_biesinger2011"), sp)
    r_all = fit(m_all, prepare(sp.be, sp.cps, m_all, acq_time=0.5), n_starts=3)
    assert sum(fl["code"] == "insignificant" for fl in r_all.flags) >= 5


@pytest.mark.parametrize("tid", ["cr2p3_biesinger2011", "mn2p3_biesinger2011", "fe2p3_biesinger2011",
                                 "co2p3_biesinger2011", "ni2p3_biesinger2011"])
def test_multiplet_tables_consistent_and_fittable(tid):
    """Every sourced table: per-species areas sum to 100 % (as printed; Cr2O3 103 %), positive widths,
    each species lies inside its preset window, and a spectrum synthesised from one species is fitted
    back with that species' reference position (± 0.15 eV) and χ²ᵣ < 2."""
    from peakforge import presets
    t = presets.multiplet_tables()[tid]
    for spn, peaks in t["species"].items():
        tot = sum(a for _be, a, _w in peaks)
        assert 97 <= tot <= 104, (spn, tot)
        assert all(w > 0 for _be, _a, w in peaks)
    rng = np.random.default_rng(3)
    spn = max(t["species"], key=lambda k: len(t["species"][k]))         # richest envelope
    peaks = t["species"][spn]
    pre = presets.multiplet_preset(tid, [spn])
    lo, hi = pre["range"]
    assert all(lo < be < hi for be, _a, _w in peaks if be < hi - 0.5) and peaks[0][0] > lo
    x = np.arange(lo - 3, hi + 3, 0.1)
    # no baseline and no background: tests the table and the preset, not the background end point (§6c)
    y = 1.0 + sum(20000 * a / 100 * lineshapes.profile("gl", x, be + 0.2, w, m=0.3) for be, a, w in peaks)
    sp = Spectrum(t["level"] + "3/2", x, rng.poisson(y) / 1.0, sample="s", meta=dict(acq_time=1.0, format="test"))
    m = presets.model_from_preset(pre, sp)
    m.background.kind = "none"
    r = fit(m, prepare(sp.be, sp.cps, m, acq_time=1.0), n_starts=2)
    first = m.components[0].name
    assert r.values[first]["center"] == pytest.approx(peaks[0][0] + 0.2, abs=0.15)
    assert r.chi2_red < 2.0, r.chi2_red


def test_backend_messages_translatable():
    """Every quality-flag and charge-reference message code has a Chinese template whose placeholders
    are the message's args (gui/i18n: user-facing strings in zh/en)."""
    import re
    from peakforge import msg as M
    from peakforge.gui import i18n
    src = ""
    for f in ("core/quality.py", "core/quant.py", "project.py"):
        with open(os.path.join(os.path.dirname(M.__file__), f), encoding="utf-8") as fh:
            src += fh.read()
    # flag codes (code="...") and Msg codes (the string literal right after the English text)
    codes = set(re.findall(r'code="(\w+)"', src)) | set(re.findall(r'"\s*,\s*"((?:ref|charge)_[a-z0-9_]+)"', src))
    assert len(codes) >= 20, codes
    assert codes <= set(i18n.MSG_ZH), codes - set(i18n.MSG_ZH)
    old = i18n._lang
    try:
        i18n._lang = "zh"
        sp = _spec("X", [(61.0, 0.9, 30000)], 55, 70, t=1.0)
        m = RegionModel(region="X", background=BackgroundSpec(kind="linear"))
        m.components.append(Component(name="A", shape="gl", params=dict(
            center=Param(61, 60, 62), fwhm=Param(1.8, 1.5, 4), area=Param(500, 0), m=Param(0.3, vary=False))))
        r = fit(m, prepare(sp.be, sp.cps, m, acq_time=1.0), n_starts=1)
        assert r.flags and all(i18n.flag_text(f) != f["text"] for f in r.flags)
        inner = M.Msg("weak peak (S/N 5)", "ref_weak", snr="5")
        outer = M.Msg("x", "charge_not_applied", region="C 1s", x="283.00", shift="+1.80", reasons=[inner])
        assert "峰太弱" in i18n.tr_msg(outer) and "+1.80" in i18n.tr_msg(outer)
        assert M.exc_msg(ValueError(inner)).code == "ref_weak"
        i18n._lang = "en"
        assert i18n.tr_msg(outer) == "x"
    finally:
        i18n._lang = old
