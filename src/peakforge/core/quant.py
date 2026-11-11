"""Quantification and charge correction."""
from __future__ import annotations

import numpy as np

from . import background as bgmod
from . import lineshapes


QUANT_METHOD = ("at% = (A/RSF) / Σ(A/RSF). Built-in RSFs are approximate Scofield photoionisation cross "
                "sections (Al Kα, C 1s = 1) WITHOUT transmission-function, inelastic-mean-free-path or "
                "angular-asymmetry corrections, so absolute at% can be biased by tens of percent; enter your "
                "instrument's RSFs for quantitative work. Fitted areas include both spin–orbit partners.")


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
    """Position of the main C 1s (C–C/C–H) peak: Shirley + single GL(30) fitted to the low-BE side and
    top of the maximum inside `window` (uncorrected BE). Raises ValueError instead of returning a
    position when the peak is not clearly inside the window (strong charging, no C 1s signal):
    the shift must then be set by hand."""
    from scipy.optimize import least_squares
    bg = bgmod.compute("shirley", x, y)
    ys = y - bg
    m = (x >= window[0]) & (x <= window[1])
    if m.sum() < 5:
        raise ValueError(f"C 1s spectrum does not cover {window[0]}–{window[1]} eV")
    i0 = int(np.argmax(np.where(m, ys, -np.inf)))
    c0 = x[i0]
    edge = 0.3
    if c0 - window[0] < edge or window[1] - c0 < edge:
        raise ValueError(f"C 1s maximum at {c0:.2f} eV is at the edge of the search window "
                         f"{window[0]}–{window[1]} eV (strong charging?) — set the shift manually")
    if ys[i0] <= 0 or ys[i0] < 5 * np.std(np.diff(y)):
        raise ValueError("no clear C 1s peak — set the shift manually")
    k = (x >= c0 - 1.5) & (x <= c0 + 1.0)   # fit the low-BE side + top, avoid C–O shoulder

    def r(p):
        a, c, w = p
        return a * lineshapes.profile("gl", x[k], c, w, m=0.3) - ys[k]
    a0 = ys[i0] * 1.3
    res = least_squares(r, [a0, c0, 1.2], bounds=([0, c0 - 1, 0.4], [np.inf, c0 + 1, 3.0]))
    c = float(res.x[1])
    if abs(c - c0) > 0.95:
        raise ValueError(f"C 1s fit did not converge near {c0:.2f} eV — set the shift manually")
    return c
