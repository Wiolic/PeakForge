"""Quantification and charge correction."""
from __future__ import annotations

import numpy as np

from . import background as bgmod
from . import lineshapes


def raw_area(x: np.ndarray, y: np.ndarray, kind: str = "shirley", lo=None, hi=None) -> float:
    """Background-subtracted integral (no peak model)."""
    bg = bgmod.compute(kind, x, y, lo, hi)
    m = np.ones_like(x, bool)
    if lo is not None:
        m &= x >= lo
    if hi is not None:
        m &= x <= hi
    return float(np.trapezoid((y - bg)[m], x[m]))


def atomic_percent(entries: list[dict]) -> list[dict]:
    """entries: [{sample, region, area, rsf}] -> adds 'at%' per sample (entries w/o RSF skipped)."""
    out = []
    samples = {}
    for e in entries:
        samples.setdefault(e["sample"], []).append(e)
    for s, es in samples.items():
        norm = [(e, e["area"] / e["rsf"]) for e in es if e.get("rsf") and e.get("area") is not None]
        tot = sum(v for _, v in norm)
        for e, v in norm:
            out.append(dict(e, normalized=v, at_pct=100 * v / tot if tot > 0 else np.nan))
    return out


def find_c1s_reference(x: np.ndarray, y: np.ndarray, window=(283.0, 287.0)) -> float:
    """Position of the main C 1s (C–C) peak: Shirley + single GL(30) fit around the maximum.
    x must be uncorrected BE."""
    from scipy.optimize import least_squares
    bg = bgmod.compute("shirley", x, y)
    ys = y - bg
    m = (x >= window[0]) & (x <= window[1])
    if m.sum() < 5:
        m = np.ones_like(x, bool)
    i0 = np.argmax(np.where(m, ys, -np.inf))
    c0 = x[i0]
    k = (x >= c0 - 1.5) & (x <= c0 + 1.0)   # fit the low-BE side + top, avoid C–O shoulder

    def r(p):
        a, c, w = p
        return a * lineshapes.profile("gl", x[k], c, w, m=0.3) - ys[k]
    a0 = ys[i0] * 1.3
    res = least_squares(r, [a0, c0, 1.2], bounds=([0, c0 - 1, 0.4], [np.inf, c0 + 1, 3.0]))
    return float(res.x[1])
