"""Least-squares fitting of a RegionModel to a Spectrum."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from . import background as bgmod
from .model import RegionModel


@dataclass
class Prepared:
    x: np.ndarray            # BE (charge corrected), ascending, cropped to fit range
    y: np.ndarray            # intensity (cps)
    bg: np.ndarray
    w: np.ndarray            # residual weights


def prepare(be: np.ndarray, cps: np.ndarray, model: RegionModel, shift: float = 0.0,
            counts: np.ndarray | None = None) -> Prepared:
    x = np.asarray(be, float) + shift
    y = np.asarray(cps, float)
    if model.fit_range:
        lo, hi = sorted(model.fit_range)
        m = (x >= lo) & (x <= hi)
        x, y = x[m], y[m]
        if counts is not None:
            counts = counts[m]
    b = model.background
    bg = bgmod.compute(b.kind, x, y, b.lo, b.hi, b.avg, tuple(b.tougaard))
    if model.weighting == "poisson" and counts is not None:
        scale = np.where(counts > 0, y / counts, 1.0)        # cps per count
        sigma = np.sqrt(np.clip(counts, 1, None)) * scale
        w = 1.0 / sigma
        w = w / np.mean(w)
    else:
        w = np.ones_like(y)
    return Prepared(x, y, bg, w)


@dataclass
class FitResult:
    ok: bool
    message: str
    values: dict[str, dict[str, float]]          # resolved parameter values
    stderr: dict[str, float]                     # 'comp.param' -> 1σ (free params only)
    free_names: list[str]
    corr: np.ndarray | None
    x: np.ndarray
    y: np.ndarray
    bg: np.ndarray
    comp_curves: dict[str, list[np.ndarray]]     # component -> [line(s)] without background
    envelope: np.ndarray                         # bg + sum(lines)
    residual: np.ndarray                         # y - envelope
    areas: dict[str, float]                      # total area per component (incl. doublet partner)
    fractions: dict[str, float]                  # % of in_total components
    rms_pct: float                               # residual RMS / max(y - bg) * 100
    chi2_red: float
    aic: float
    bic: float
    n_free: int
    bound_hits: list[str]
    starts: list[dict] = field(default_factory=list)   # multi-start summary
    nfev: int = 0

    def summary_rows(self, model: RegionModel) -> list[dict]:
        rows = []
        for c in model.components:
            v = self.values[c.name]
            row = dict(component=c.name, label=c.label, shape=c.shape,
                       center=v["center"], center_err=self.stderr.get(f"{c.name}.center"),
                       fwhm=v["fwhm"], fwhm_err=self.stderr.get(f"{c.name}.fwhm"),
                       area=self.areas[c.name], area_err=self.stderr.get(f"{c.name}.area"),
                       fraction=self.fractions.get(c.name))
            if c.doublet:
                row["center2"] = v["center"] + v["split"]
                row["split"] = v["split"]
                row["ratio"] = v["ratio"]
            for k in c.shape_kw(v):
                row[k] = v[k]
            rows.append(row)
        return rows

    def to_json(self, model: RegionModel) -> dict:
        return dict(ok=self.ok, message=self.message, rms_pct=self.rms_pct, chi2_red=self.chi2_red,
                    aic=self.aic, bic=self.bic, n_free=self.n_free, bound_hits=self.bound_hits,
                    fractions=self.fractions, areas=self.areas, values=self.values,
                    stderr=self.stderr, components=self.summary_rows(model), starts=self.starts)


def _free_vector(model: RegionModel):
    names, p0, lb, ub = [], [], [], []
    for key, c, k, p in model.param_items():
        if p.free:
            lo = p.min if np.isfinite(p.min) else -np.inf
            hi = p.max if np.isfinite(p.max) else np.inf
            if hi - lo < 1e-12:
                continue
            names.append(key)
            p0.append(min(max(p.value, lo), hi))
            lb.append(lo)
            ub.append(hi)
    return names, np.array(p0, float), np.array(lb, float), np.array(ub, float)


def evaluate(model: RegionModel, x: np.ndarray, overrides=None):
    vals = model.resolve(overrides)
    curves = {c.name: c.lines(x, vals[c.name]) for c in model.components}
    total = np.zeros_like(x)
    for ls in curves.values():
        for l_ in ls:
            total += l_
    return vals, curves, total


def fit(model: RegionModel, prep: Prepared, n_starts: int = 1, seed: int = 0,
        max_nfev: int = 4000, optimize: bool = True) -> FitResult:
    """Fit (or, with optimize=False, just evaluate the current parameter values)."""
    names, p0, lb, ub = _free_vector(model)
    ysub = prep.y - prep.bg
    span = float(np.trapezoid(np.clip(ysub, 0, None), prep.x)) or 1.0

    def resid(p):
        _, _, tot = evaluate(model, prep.x, dict(zip(names, p)))
        return (tot - ysub) * prep.w

    best, starts = None, []
    rng = np.random.default_rng(seed)
    if len(names) == 0 or not optimize:
        r = None
    else:
        for k in range(max(1, n_starts)):
            if k == 0:
                q0 = p0.copy()
            else:
                q0 = p0.copy()
                for i, n in enumerate(names):
                    lo, hi = lb[i], ub[i]
                    if n.endswith(".area"):
                        q0[i] = rng.uniform(0.05, 0.8) * span
                    elif np.isfinite(lo) and np.isfinite(hi):
                        q0[i] = lo + rng.uniform(0.05, 0.95) * (hi - lo)
                    else:
                        q0[i] = p0[i] * rng.uniform(0.8, 1.2) + rng.normal(0, 0.1)
                q0 = np.clip(q0, lb, ub)
            try:
                r = least_squares(resid, q0, bounds=(lb, ub), x_scale="jac", max_nfev=max_nfev)
            except Exception as e:      # noqa: BLE001
                starts.append(dict(start=k, cost=np.inf, error=str(e)))
                continue
            starts.append(dict(start=k, cost=float(r.cost), x=r.x.tolist()))
            if best is None or r.cost < best.cost:
                best = r
        r = best
    pbest = dict(zip(names, r.x)) if r is not None else {}
    vals, curves, tot = evaluate(model, prep.x, pbest)
    env = prep.bg + tot
    res = prep.y - env
    n, k = len(prep.x), len(names)
    peak_h = max(float(np.max(ysub)), 1e-12)
    rms_pct = float(np.sqrt(np.mean(res ** 2)) / peak_h * 100)
    wres = res * prep.w
    rss = float(np.sum(wres ** 2))
    dof = max(n - k, 1)
    # reduced chi² (only meaningful with Poisson weighting; otherwise relative to data noise estimate)
    if model.weighting == "poisson":
        chi2_red = rss / dof
    else:
        noise = np.std(np.diff(prep.y)) / np.sqrt(2) or 1.0
        chi2_red = float(np.sum(res ** 2) / noise ** 2 / dof)
    aic = n * np.log(rss / n + 1e-300) + 2 * k
    bic = n * np.log(rss / n + 1e-300) + k * np.log(n)

    stderr, corr = {}, None
    if r is not None and k > 0:
        J = r.jac
        try:
            cov = np.linalg.pinv(J.T @ J) * (rss / dof)
            sd = np.sqrt(np.clip(np.diag(cov), 0, None))
            stderr = {nm: float(s) for nm, s in zip(names, sd)}
            with np.errstate(invalid="ignore", divide="ignore"):
                corr = cov / np.outer(sd, sd)
        except np.linalg.LinAlgError:
            pass

    hits = []
    for i, nm in enumerate(names if r is not None else []):
        v, lo, hi = r.x[i], lb[i], ub[i]
        rng_ = (hi - lo) if np.isfinite(hi - lo) and hi > lo else max(abs(v), 1.0)
        if nm.endswith(".area") and lo == 0:
            if v <= 1e-9 * span:
                hits.append(nm + " = 0")
            continue
        if np.isfinite(lo) and (v - lo) / rng_ < 0.005:
            hits.append(nm + " @min")
        elif np.isfinite(hi) and (hi - v) / rng_ < 0.005:
            hits.append(nm + " @max")

    areas = {c.name: c.total_area(vals[c.name]) for c in model.components}
    tot_in = sum(a for c in model.components if c.in_total for a in [areas[c.name]])
    fractions = {c.name: (100 * areas[c.name] / tot_in if tot_in > 0 else float("nan"))
                 for c in model.components if c.in_total}
    msg = r.message if r is not None else ("evaluated (not fitted)" if not optimize else "no free parameters")
    ok = bool(r.success) if r is not None else True
    for s in starts:
        s.pop("x", None)
    return FitResult(ok=ok, message=str(msg), values=vals, stderr=stderr, free_names=names, corr=corr,
                     x=prep.x, y=prep.y, bg=prep.bg, comp_curves=curves, envelope=env, residual=res,
                     areas=areas, fractions=fractions, rms_pct=rms_pct, chi2_red=float(chi2_red),
                     aic=float(aic), bic=float(bic), n_free=k, bound_hits=hits, starts=starts,
                     nfev=int(r.nfev) if r is not None else 0)


def apply_result(model: RegionModel, res: FitResult):
    """Write fitted values back into the model's parameters (expressions stay as they are)."""
    for c in model.components:
        for k, p in c.params.items():
            p.value = float(res.values[c.name][k])
