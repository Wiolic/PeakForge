"""Inelastic backgrounds. x is binding energy (ascending), y intensity.

kinds:
  none      zero
  linear    straight line between averaged end points
  shirley   iterative Shirley (Sherwood) between averaged end points
  tougaard  Tougaard background with the cross section
              K(T) = B·T / ((C − T²)² + D·T²)            (U3; Tougaard, SIA 25 (1997) 137)
            D = 4C makes it identical to the universal two-parameter U2 = B·T / (C + T²)²
            (Tougaard 1989; C = 1643 eV² for metals, their alloys and oxides). B is NOT used as
            given: the background is rescaled to meet the averaged high-BE end point.
  smart     Shirley, but clipped so it never exceeds the data (CasaXPS 'Smart')
"""
from __future__ import annotations

import numpy as np

KINDS = ("shirley", "linear", "tougaard", "smart", "none")

# (B, C, D) for K(T) = B·T / ((C − T²)² + D·T²). C, D in eV², from S. Tougaard, Surf. Interface Anal.
# 56 (2024), doi:10.1002/sia.7273, eqs. 1–2, citing Surf. Interface Anal. 25 (1997) 137. B is rescaled.
TOUGAARD_U2 = (2866.0, 1643.0, 4 * 1643.0)
TOUGAARD_PRESETS = {
    "U2 universal": TOUGAARD_U2,          # metals, alloys, oxides
    "U3 Al": (1.0, 230.0, 4.5),
    "U3 Si": (1.0, 325.0, 96.0),
    "U3 polymer": (1.0, 551.0, 436.0),
}
_OLD_DEFAULT = (2866.0, 1643.0, 1.0)      # PeakForge 0.1 default: not a physical cross section


def normalize_tougaard(t) -> tuple:
    """Return a valid (B, C, D); maps the 0.1 default (2866, 1643, 1) to U2."""
    t = tuple(float(v) for v in (t or TOUGAARD_U2))
    return TOUGAARD_U2 if t == _OLD_DEFAULT or len(t) != 3 else t


def _ends(x, y, lo, hi, avg):
    m_lo = (x >= lo) & (x <= lo + avg)
    m_hi = (x <= hi) & (x >= hi - avg)
    y_lo = y[m_lo].mean() if m_lo.any() else y[np.argmin(np.abs(x - lo))]
    y_hi = y[m_hi].mean() if m_hi.any() else y[np.argmin(np.abs(x - hi))]
    return y_lo, y_hi


def end_point_response(kind: str, x: np.ndarray, y: np.ndarray, lo: float | None = None,
                       hi: float | None = None, avg: float = 0.5, tougaard: tuple = None) -> list:
    """Linear response of the background to its two end-point averages, for error propagation.
    Returns [(g, u), ...]: u = weights of the data points forming the end-point average (sums to 1),
    g = ∂background/∂(that average), by finite difference. The background depends on the data mainly
    through these averages (checked against the full ∂bg/∂y: within 3 %, docs/METHODS.md)."""
    if kind == "none" or len(x) < 2:
        return []
    tougaard = TOUGAARD_U2 if tougaard is None else tougaard
    lo_ = x.min() if lo is None else max(lo, x.min())
    hi_ = x.max() if hi is None else min(hi, x.max())
    base = compute(kind, x, y, lo, hi, avg, tougaard)
    h = max(1e-6 * float(np.max(np.abs(y))), 1e-9)
    out = []
    for win in ((x >= lo_) & (x <= lo_ + avg), (x <= hi_) & (x >= hi_ - avg)):
        if not win.any():
            win = np.zeros(len(x), bool)
            win[np.argmin(np.abs(x - (lo_ if not out else hi_)))] = True
        u = win / win.sum()
        g = (compute(kind, x, y + h * win, lo, hi, avg, tougaard) - base) / h
        out.append((g, u))
    return out


def auto_limits(x: np.ndarray, y: np.ndarray, frac: float = 0.25, smooth: int = 5) -> tuple[float, float]:
    """Background end points: minimum of the smoothed spectrum within the outer `frac` of each side.
    Avoids anchoring the background on the rising tail of a neighbouring peak."""
    o = np.argsort(x)
    xs, ys = x[o], y[o]
    k = max(1, smooth)
    ysm = np.convolve(ys, np.ones(k) / k, mode="same")
    n = len(xs)
    e = max(2, int(n * frac))
    lo_i = int(np.argmin(ysm[k // 2: e])) + k // 2
    hi_i = n - e + int(np.argmin(ysm[n - e: n - k // 2]))
    return float(xs[lo_i]), float(xs[hi_i])


def compute(kind: str, x: np.ndarray, y: np.ndarray, lo: float | None = None,
            hi: float | None = None, avg: float = 0.5, tougaard: tuple = TOUGAARD_U2,
            n_iter: int = 100) -> np.ndarray:
    """Background over the whole x array; outside [lo, hi] it is held at the end values."""
    lo = x.min() if lo is None else max(lo, x.min())
    hi = x.max() if hi is None else min(hi, x.max())
    if kind == "none":
        return np.zeros_like(y)
    y_lo, y_hi = _ends(x, y, lo, hi, avg)
    m = (x >= lo) & (x <= hi)
    xs, ys = x[m], y[m]
    if kind == "linear":
        b = np.interp(x, [lo, hi], [y_lo, y_hi])
        return b
    if kind in ("shirley", "smart"):
        b = np.full_like(ys, y_lo)
        for _ in range(n_iter):
            s = ys - b
            if kind == "smart":
                s = np.clip(s, 0, None)
            cum = np.concatenate([[0.0], np.cumsum(0.5 * (s[1:] + s[:-1]) * np.diff(xs))])
            tot = cum[-1] if abs(cum[-1]) > 1e-30 else 1.0
            b_new = y_lo + (y_hi - y_lo) * cum / tot
            if kind == "smart":
                b_new = np.minimum(b_new, ys)
            if np.max(np.abs(b_new - b)) < 1e-7 * max(abs(y_hi), 1.0):
                b = b_new
                break
            b = b_new
        out = np.empty_like(y)
        out[m] = b
        out[x < lo] = y_lo
        out[x > hi] = y_hi
        return out
    if kind == "tougaard":
        B, C, D = normalize_tougaard(tougaard)
        # K(T) = B T / ((C - T^2)^2 + D T^2); electrons emitted at BE x' that lose energy T appear at
        # BE x = x' + T, so bg(x) = ∫_{x' < x} K(x - x') j(x') dx'
        j = ys - y_lo
        dx = np.mean(np.diff(xs)) if len(xs) > 1 else 1.0
        n = len(xs)
        T = np.arange(n) * dx
        K = B * T / ((C - T ** 2) ** 2 + D * T ** 2)
        bg = np.array([np.sum(K[:i + 1][::-1] * j[:i + 1]) * dx for i in range(n)])
        # scale B so the background meets the high-BE end
        if bg[-1] != 0:
            bg *= (y_hi - y_lo) / bg[-1]
        b = y_lo + bg
        out = np.empty_like(y)
        out[m] = b
        out[x < lo] = y_lo
        out[x > hi] = b[-1]
        return out
    raise ValueError(f"unknown background kind {kind}")
