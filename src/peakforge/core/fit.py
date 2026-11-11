"""Least-squares fitting of a RegionModel to a Spectrum."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.optimize import least_squares

from . import background as bgmod
from . import lineshapes
from .model import RegionModel


# shapes whose 'fwhm' parameter is not the measured full width at half maximum
_FWHM_NOT_EXACT = ("gl", "ds", "la")


@dataclass
class Prepared:
    x: np.ndarray            # BE (charge corrected), ascending, cropped to fit range
    y: np.ndarray            # intensity (cps)
    bg: np.ndarray
    w: np.ndarray            # relative residual weights (mean 1)
    sigma: np.ndarray | None = None     # absolute 1σ noise per point (cps), used for χ²ᵣ
    noise: str = "estimated"            # 'counting' (known acquisition time) | 'estimated' (from data)
    noise_ratio: float = float("nan")   # data noise / counting-statistics noise (variance ratio)
    acq_time: float | None = None       # s per point (counting noise), None = estimated from the data
    shaped: bool = True                 # noise variance ∝ intensity (False: constant, e.g. subtracted data)


_MEDIAN_CHI2_1 = 0.454936                # median of χ² with one degree of freedom


def _residual_noise_scale(res: np.ndarray, level: np.ndarray | None) -> float:
    """Post-fit noise level k (var = k·level, or var = k if level is None) from 4th differences of the
    fit residual: d_i = r_{i−2} − 4r_{i−1} + 6r_i − 4r_{i+1} + r_{i+2}, var(d) = 70σ² for white noise.
    The fitted model removes the peak structure and the 4th difference removes what is left of smooth
    misfit, so peaks filling the window or coarse steps no longer inflate k (docs/METHODS.md)."""
    if len(res) < 9:
        return float("nan")
    d = res[:-4] - 4 * res[1:-3] + 6 * res[2:-2] - 4 * res[3:-1] + res[4:]
    q = d ** 2 / 70.0
    if level is not None:
        q = q / level[2:-2]
    return float(np.median(q) / _MEDIAN_CHI2_1)


def _noise_scale(y: np.ndarray) -> tuple[float, bool]:
    """Robust estimate of k in var(y_i) = k·y_i (Poisson-shaped, cps data) from second differences
    r_i = y_i − (y_{i−1}+y_{i+1})/2, var(r_i) = 1.5 var(y). The median makes it insensitive to the
    curvature of sharp peaks. Returns (k, poisson_shaped); for data with y <= 0 (background-subtracted
    tables) a constant variance k is returned instead."""
    if len(y) < 5:
        return float("nan"), False
    r = y[1:-1] - 0.5 * (y[:-2] + y[2:])
    # local level from a 5-point mean, so the denominator is not correlated with r_i itself
    ym = np.convolve(y, np.ones(5) / 5, mode="same")[1:-1]
    ym[:1], ym[-1:] = y[1:2], y[-2:-1]
    if np.all(ym > 0):
        return float(np.median(r ** 2 / (1.5 * ym)) / _MEDIAN_CHI2_1), True
    return float(np.median(r ** 2 / 1.5) / _MEDIAN_CHI2_1), False


def prepare(be: np.ndarray, cps: np.ndarray, model: RegionModel, shift: float = 0.0,
            counts: np.ndarray | None = None, acq_time: float | None = None) -> Prepared:
    """Crop to the fit window, compute the background and the noise model.
    acq_time: seconds per point such that cps·acq_time are Poisson counts (Spectrum.acq_time());
    None -> the noise level is estimated from the data. `counts` is accepted for backward compatibility."""
    x = np.asarray(be, float) + shift
    y = np.asarray(cps, float)
    if acq_time is None and counts is not None:
        c = np.asarray(counts, float)
        ok = (y > 0) & (c > 0)
        acq_time = float(np.median(c[ok] / y[ok])) if ok.any() else None
    if model.fit_range:
        lo, hi = sorted(model.fit_range)
        m = (x >= lo) & (x <= hi)
        x, y = x[m], y[m]
    b = model.background
    bg = bgmod.compute(b.kind, x, y, b.lo, b.hi, b.avg, tuple(b.tougaard))
    k, shaped = _noise_scale(y)
    if acq_time:
        t = float(acq_time)
        sigma = np.sqrt(np.clip(y * t, 1.0, None)) / t
        noise, ratio = "counting", (k * t if shaped else float("nan"))
    elif np.isfinite(k) and k > 0:
        sigma = np.sqrt(k * np.clip(y, 1e-12, None)) if shaped else np.full_like(y, np.sqrt(k))
        noise, ratio = "estimated", float("nan")
    else:
        sigma, noise, ratio = None, "estimated", float("nan")
    if model.weighting == "poisson" and sigma is not None:
        w = 1.0 / sigma
        w = w / np.mean(w)
    else:
        w = np.ones_like(y)
    return Prepared(x, y, bg, w, sigma, noise, float(ratio),
                    float(acq_time) if acq_time else None, bool(shaped) or bool(acq_time))


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
    noise: str = "estimated"                     # basis of χ²ᵣ: 'counting' | 'estimated'
    noise_ratio: float = float("nan")            # data noise / counting noise (variance), counting only

    def summary_rows(self, model: RegionModel) -> list[dict]:
        rows = []
        for c in model.components:
            v = self.values[c.name]
            row = dict(component=c.name, label=c.label, shape=c.shape,
                       center=v["center"], center_err=self.stderr.get(f"{c.name}.center"),
                       fwhm=v["fwhm"], fwhm_err=self.stderr.get(f"{c.name}.fwhm"),
                       area=self.areas[c.name], area_err=self.stderr.get(f"{c.name}.total_area"),
                       fraction=self.fractions.get(c.name),
                       fraction_err=self.stderr.get(f"{c.name}.fraction"))
            if c.shape in _FWHM_NOT_EXACT:
                row["fwhm_apparent"] = lineshapes.apparent_fwhm(c.shape, v["fwhm"], **c.shape_kw(v))
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
                    noise=self.noise, noise_ratio=None if not np.isfinite(self.noise_ratio) else self.noise_ratio,
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


def _derived_quantities(model: RegionModel, names, p) -> dict[str, float]:
    vals = model.resolve(dict(zip(names, p)))
    out = {f"{c.name}.{k}": v for c in model.components for k, v in vals[c.name].items()}
    areas = {c.name: c.total_area(vals[c.name]) for c in model.components}
    tot = sum(areas[c.name] for c in model.components if c.in_total)
    for c in model.components:
        out[f"{c.name}.total_area"] = areas[c.name]
        if c.in_total and tot > 0:
            out[f"{c.name}.fraction"] = 100 * areas[c.name] / tot
    return out


def _derived_errors(model: RegionModel, names, p, cov) -> dict[str, float]:
    """Linear error propagation σ²_g = ∇g · Cov · ∇gᵀ for every resolved parameter (including
    expression-linked ones), total doublet area and % fraction. Free parameters keep their own σ.
    The covariance already contains the background end-point noise (see fit())."""
    g0 = _derived_quantities(model, names, p)
    keys = list(g0)
    G = np.zeros((len(keys), len(p)))
    for j in range(len(p)):
        h = 1e-6 * max(abs(p[j]), 1e-3)
        q1, q2 = p.copy(), p.copy()
        q1[j] += h
        q2[j] -= h
        g1, g2 = _derived_quantities(model, names, q1), _derived_quantities(model, names, q2)
        G[:, j] = [(g1.get(k, np.nan) - g2.get(k, np.nan)) / (2 * h) for k in keys]
    var = np.einsum("ij,jk,ik->i", G, cov, G)
    free = set(names)
    return {k: float(np.sqrt(max(v, 0.0))) for k, v in zip(keys, var) if k not in free and np.isfinite(v)}


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
    # post-fit noise level from the residual (unbiased by peak curvature, see _residual_noise_scale)
    # The variance model (∝ intensity or constant) is the one prepare() chose from the data; the level
    # is the fitted envelope. Zero-centred (background-subtracted) data keep constant variance.
    sigma, noise_ratio = prep.sigma, prep.noise_ratio
    shaped = prep.shaped and bool(np.all(env > 0))
    k_post = _residual_noise_scale(res, env if shaped else None) * n / dof   # residuals lose ~k/n of the variance
    if np.isfinite(k_post) and k_post > 0:
        if prep.noise == "counting":
            noise_ratio = k_post * prep.acq_time if shaped else float("nan")
        else:
            sigma = np.sqrt(k_post * np.clip(prep.y, 1e-12, None)) if shaped else np.full_like(prep.y, np.sqrt(k_post))
    # reduced χ² against the absolute noise model (counting statistics or estimated), whatever the weighting
    chi2_red = float(np.sum((res / sigma) ** 2) / dof) if sigma is not None else float("nan")
    aic = n * np.log(rss / n + 1e-300) + 2 * k
    bic = n * np.log(rss / n + 1e-300) + k * np.log(n)

    stderr, corr = {}, None
    if r is not None and k > 0:
        J = r.jac
        try:
            A = np.linalg.pinv(J.T @ J)
            if sigma is not None and np.isfinite(chi2_red):
                # Linear propagation of the data noise into the parameters, Δp = A·Jᵀ·W·(I − G)·Δy:
                # sandwich covariance A·M·Σ·Mᵀ·A, M = Jᵀ·W·(I − G), Σ = σ²·χ²ᵣ (χ²ᵣ absorbs misfit and the
                # scale of an estimated noise level). G = ∂background/∂y through the two end-point averages
                # (the background is computed from the same noisy data). Correct also for unweighted fits.
                M = J.T * prep.w
                b = model.background
                for g, u in bgmod.end_point_response(b.kind, prep.x, prep.y, b.lo, b.hi, b.avg,
                                                     tuple(b.tougaard)):
                    M = M - np.outer(J.T @ (prep.w * g), u)
                cov = A @ (M * (sigma ** 2 * chi2_red)) @ M.T @ A
            else:
                cov = A * (rss / dof)
            sd = np.sqrt(np.clip(np.diag(cov), 0, None))
            stderr = {nm: float(s) for nm, s in zip(names, sd)}
            with np.errstate(invalid="ignore", divide="ignore"):
                corr = cov / np.outer(sd, sd)
            stderr.update(_derived_errors(model, names, r.x, cov))
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
                     nfev=int(r.nfev) if r is not None else 0, noise=prep.noise, noise_ratio=float(noise_ratio))


def apply_result(model: RegionModel, res: FitResult):
    """Write fitted values back into the model's parameters (expressions stay as they are)."""
    for c in model.components:
        for k, p in c.params.items():
            p.value = float(res.values[c.name][k])
