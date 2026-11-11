"""Fit-quality diagnostics: bound hits, parameter correlations, component significance (ΔBIC on
removal), multi-start stability."""
from __future__ import annotations

from collections.abc import Callable

import numpy as np

from .fit import FitResult, Prepared, apply_result, fit
from .model import RegionModel


def correlations(res: FitResult, threshold: float = 0.95) -> list[dict]:
    out = []
    if res.corr is None:
        return out
    n = len(res.free_names)
    for i in range(n):
        for j in range(i + 1, n):
            r = res.corr[i, j]
            if np.isfinite(r) and abs(r) >= threshold:
                out.append(dict(a=res.free_names[i], b=res.free_names[j], r=float(r)))
    return sorted(out, key=lambda d: -abs(d["r"]))


def _without(model: RegionModel, name: str) -> RegionModel | None:
    m = model.copy()
    m.components = [c for c in m.components if c.name != name]
    # any expression pointing at the removed component -> freeze at current value
    for key, c, k, p in m.param_items():
        if p.expr and f"{name}." in p.expr:
            vals = model.resolve()
            p.value = vals[c.name][k]
            p.expr = None
    return m if m.components else None


def _report(progress: Callable[[float, str], None] | None, f: float, text: str) -> None:
    if progress is not None:
        progress(f, text)


def significance(model: RegionModel, prep: Prepared, base: FitResult, n_starts: int = 1,
                 progress: Callable[[float, str], None] | None = None, check: Callable[[], None] | None = None,
                 span: tuple[float, float] = (0.0, 1.0)) -> list[dict]:
    """Refit with each component removed; ΔBIC > 10 = component strongly supported,
    2..10 = positive evidence, < 2 = not supported by the data.
    progress / check: optional reporting and cancellation hooks (peakforge.tasks); they never change results."""
    out = []
    n = max(len(model.components), 1)
    for i, c in enumerate(model.components):
        m = _without(model, c.name)
        if m is None:
            continue
        _report(progress, span[0] + (span[1] - span[0]) * i / n, f"ΔBIC {c.label}")
        r = fit(m, prep, n_starts=n_starts, check=check)
        d_bic = r.bic - base.bic
        if d_bic < -10 and r.rms_pct < base.rms_pct:
            verdict = "local minimum"     # the smaller model fits better -> full fit is not at its optimum
        else:
            verdict = "strong" if d_bic > 10 else ("positive" if d_bic > 2 else "not supported")
        out.append(dict(component=c.name, label=c.label, rms_without=r.rms_pct, rms_with=base.rms_pct,
                        d_rms=r.rms_pct - base.rms_pct, d_bic=float(d_bic), verdict=verdict))
    return out


def stability(model: RegionModel, prep: Prepared, n_starts: int = 12, tol: float = 0.02,
              progress: Callable[[float, str], None] | None = None, check: Callable[[], None] | None = None,
              span: tuple[float, float] = (0.0, 1.0)) -> dict:
    """Run n random starts; among solutions within (1+tol)·best cost, report fraction spread."""
    sols = []
    for s in range(n_starts):
        _report(progress, span[0] + (span[1] - span[0]) * s / max(n_starts, 1), f"{s + 1}/{n_starts}")
        r = fit(model, prep, n_starts=1 if s == 0 else 2, seed=s, check=check)
        sols.append(r)
    best = min(sols, key=lambda r: np.sum(r.residual ** 2))
    c0 = np.sum(best.residual ** 2)
    near = [r for r in sols if np.sum(r.residual ** 2) <= c0 * (1 + tol)]
    spread = {}
    for k in best.fractions:
        v = [r.fractions.get(k, np.nan) for r in near]
        spread[k] = dict(mean=float(np.nanmean(v)), std=float(np.nanstd(v)),
                         min=float(np.nanmin(v)), max=float(np.nanmax(v)))
    return dict(n_starts=n_starts, n_equivalent=len(near), fractions=spread)


def diagnose(model: RegionModel, prep: Prepared, res: FitResult, deep: bool = False,
             progress: Callable[[float, str], None] | None = None, check: Callable[[], None] | None = None) -> dict:
    d = dict(rms_pct=res.rms_pct, chi2_red=res.chi2_red, bic=res.bic, bound_hits=res.bound_hits,
             correlations=correlations(res))
    warnings = []
    if res.bound_hits:
        warnings.append("Parameters at bounds: " + ", ".join(res.bound_hits))
    if d["correlations"]:
        warnings.append("Highly correlated parameters: " +
                        ", ".join(f"{c['a']}~{c['b']} ({c['r']:+.2f})" for c in d["correlations"][:5]))
    if res.noise == "counting" and np.isfinite(res.noise_ratio) and not 0.5 < res.noise_ratio < 2.0:
        msg = (f"Data noise is {res.noise_ratio:.1f}× the counting-statistics variance expected from "
               "the file's acquisition time — χ²ᵣ and Poisson weights are unreliable (check dwell/sweeps)")
        if res.noise_ratio > 2.0 and res.chi2_red > 2.0:
            msg += ("; with χ²ᵣ ≫ 1 this can also be line-shape misfit that varies from point to point "
                    "(coarse energy step)")
        warnings.append(msg)
    if res.noise == "estimated":
        d["chi2_note"] = "χ²ᵣ uses a noise level estimated from the data (±~15 %)"
    if res.rms_pct > 3:
        warnings.append(f"Residual RMS {res.rms_pct:.1f}% of peak height — model may be missing a component")
    if deep:
        d["significance"] = significance(model, prep, res, progress=progress, check=check, span=(0.0, 0.5))
        for s in d["significance"]:
            if s["verdict"] == "not supported":
                warnings.append(f"Component {s['label']} not supported by data (ΔBIC {s['d_bic']:.1f})")
            elif s["verdict"] == "local minimum":
                warnings.append(f"Removing {s['label']} gives a better fit (ΔRMS {s['d_rms']:+.2f} %): the "
                                "current solution is a local minimum or this component is misplaced — "
                                "refit with more starts or revise its bounds")
        d["stability"] = stability(model, prep, progress=progress, check=check, span=(0.5, 1.0))
        for k, s in d["stability"]["fractions"].items():
            if s["std"] > 3:
                warnings.append(f"Fraction of {k} unstable across starts (±{s['std']:.1f} %)")
    d["warnings"] = warnings
    return d


__all__ = ["diagnose", "significance", "stability", "correlations", "apply_result"]
