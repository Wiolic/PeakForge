"""Quantification and charge correction."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..msg import Msg
from . import background as bgmod
from . import lineshapes


QUANT_METHOD = ("at% = (A/RSF) / Σ(A/RSF). Built-in RSFs are approximate Scofield photoionisation cross "
                "sections (Al Kα, C 1s = 1) WITHOUT transmission-function, inelastic-mean-free-path or "
                "angular-asymmetry corrections, so absolute at% can be biased by tens of percent; enter your "
                "instrument's RSFs for quantitative work. Fitted areas include both spin–orbit partners.")


def raw_area(x: np.ndarray, y: np.ndarray, kind: str = "shirley", lo: float | None = None,
             hi: float | None = None) -> float:
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


@dataclass
class Reference:
    """Located charge-reference peak (uncorrected BE)."""
    position: float                 # fitted peak position (eV, uncorrected)
    fwhm: float                     # fitted GL(30) width parameter (eV)
    snr: float                      # peak prominence / point noise
    confidence: str                 # 'high' -> may be applied automatically; 'low' -> ask the user
    reasons: list[str] = field(default_factory=list)   # why the confidence is low (English)
    peaks: list[float] = field(default_factory=list)   # all prominent maxima in the search range
    notes: list[str] = field(default_factory=list)     # warnings that do not block the result (English)


# Limits of an automatic reference (METHODS §7). Shifts outside MAX_SHIFT are physically possible
# (no neutraliser: several eV positive charging) but then a wrong line is equally likely -> user decides.
REF_SPAN = (-6.0, 6.0)          # search: reference BE + span (uncorrected)
REF_MAX_SHIFT = (-3.0, 4.0)     # |shift| range accepted without asking: ref − position
REF_MIN_SNR = 8.0
REF_MAX_FWHM = 2.8              # eV; broader = mixed species / differential charging
REF_MIN_REL_PROMINENCE = 0.1    # of the most prominent peak in the search range


def _point_noise(y: np.ndarray) -> float:
    """Robust per-point noise from second differences (MAD); peaks covering a minority of the points
    do not affect the median. Slightly conservative on steep, finely sampled peaks."""
    d = np.diff(y, 2)
    return float(1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(6.0))


def find_reference(x: np.ndarray, y: np.ndarray, ref: float,
                   span: tuple[float, float] = REF_SPAN, fluoro_check: bool = False) -> Reference:
    """Locate a charge-reference line: the LOWEST-BE prominent maximum within ref + span (uncorrected).
    C–C/C–H is the lowest-BE carbon species (C–O, C=O, CF₂ and the K 2p / Ir 4d lines that share a C 1s
    window all lie above it); Au 4f7/2, a metal 4f7/2 or lattice O 1s are likewise the lowest-BE member.
    Position from a GL(30) + linear background fitted locally (c−2 … c+1 eV), so strong lines elsewhere in
    the window do not bias it. Raises ValueError when there is no peak; otherwise returns a Reference
    whose confidence is 'low' (with reasons) when it should not be applied without the user.
    fluoro_check (C 1s): note a CF₂-like peak above C–C (insulating fluoropolymer, differential charging)."""
    from scipy.optimize import least_squares
    from scipy.signal import find_peaks, savgol_filter
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    m = (x >= ref + span[0]) & (x <= ref + span[1])
    if m.sum() < 5:
        lo_, hi_ = f"{ref + span[0]:.1f}", f"{ref + span[1]:.1f}"
        raise ValueError(Msg(f"spectrum does not cover {lo_}–{hi_} eV", "ref_no_cover", lo=lo_, hi=hi_))
    step = float(np.median(np.diff(x)))
    win = max(5, int(round(0.6 / step)) | 1)
    ys = savgol_filter(y, win, 2) if len(y) > win + 2 else y
    sig = max(_point_noise(y), 1e-12)
    idx, props = find_peaks(ys, prominence=5 * sig)
    cand = [(int(i), float(p)) for i, p in zip(idx, props["prominences"]) if m[i]]
    if not cand:
        lo_, hi_ = f"{ref + span[0]:.1f}", f"{ref + span[1]:.1f}"
        raise ValueError(Msg(f"no clear peak within {lo_}–{hi_} eV — set the shift manually", "ref_no_peak",
                             lo=lo_, hi=hi_))
    pmax = max(p for _, p in cand)
    good = [(i, p) for i, p in cand if p >= REF_MIN_REL_PROMINENCE * pmax]
    i0, p0 = min(good, key=lambda t: x[t[0]])
    c0 = float(x[i0])
    k = (x >= c0 - 2.0) & (x <= c0 + 1.0)
    if k.sum() < 5:
        raise ValueError(Msg(f"too few points around {c0:.2f} eV — set the shift manually", "ref_few_points",
                             x=f"{c0:.2f}"))
    xk, yk = x[k], y[k]

    def model(p: np.ndarray) -> np.ndarray:
        a, c, w, b0, b1 = p
        return a * lineshapes.profile("gl", xk, c, w, m=0.3) + b0 + b1 * (xk - c0)
    base = float(np.min(yk))
    res = least_squares(lambda p: model(p) - yk, [p0 * 1.5, c0, 1.2, base, 0.0],
                        bounds=([0, c0 - 0.8, 0.3, -np.inf, -np.inf], [np.inf, c0 + 0.8, 4.0, np.inf, np.inf]))
    c, w = float(res.x[1]), float(res.x[2])
    reasons = []
    shift = ref - c
    if not REF_MAX_SHIFT[0] <= shift <= REF_MAX_SHIFT[1]:
        reasons.append(Msg(f"large shift {shift:+.2f} eV (charging, or a different line) — check by hand",
                           "ref_large_shift", shift=f"{shift:+.2f}"))
    snr = p0 / sig
    if snr < REF_MIN_SNR:
        reasons.append(Msg(f"weak peak (S/N {snr:.0f})", "ref_weak", snr=f"{snr:.0f}"))
    if w > REF_MAX_FWHM:
        reasons.append(Msg(f"broad peak (FWHM parameter {w:.1f} eV: several species or differential charging)",
                           "ref_broad", w=f"{w:.1f}"))
    if abs(c - c0) > 0.6:
        reasons.append(Msg(f"fit moved {c - c0:+.2f} eV from the maximum", "ref_moved", d=f"{c - c0:+.2f}"))
    # unresolved component on the LOW-BE side: a separate curvature minimum (2nd derivative of the
    # smoothed data) 0.5–2 eV below the maximum, significant against the noise of the derivative
    w2 = max(7, int(round(1.2 / step)) | 1)            # derivatives need ~1.2 eV of smoothing
    if len(y) > w2 + 2:
        d2 = -savgol_filter(y, w2, 3, deriv=2)
        n2 = 1.4826 * np.median(np.abs(d2 - np.median(d2)))
        j, _ = find_peaks(d2)
        sh = [int(i) for i in j if c0 - 2.0 <= x[i] <= c0 - 0.5 and d2[i] > max(4 * n2, 0.1 * d2[i0])]
        if sh:
            reasons.append(Msg(f"shoulder on the low-BE side near {x[sh[-1]]:.1f} eV "
                               "(the reference species may be the shoulder)", "ref_shoulder", x=f"{x[sh[-1]]:.1f}"))
    notes = []
    if fluoro_check:
        # CF₂-like peak 6.5–7.5 eV above C–C (separation measured on PHI data of Nafion-containing samples:
        # 6.7–7.4 eV; K 2p3/2 of KOH residue lies at +7.6–7.8 there): fluoropolymer (e.g. Nafion) is an insulator -> differential charging between the
        # membrane and the active material is possible; the C–C reference may not apply to the other phases.
        fl = [float(x[i]) for i, p in zip(idx, props["prominences"])
              if c + 6.5 <= x[i] <= c + 7.5 and p >= 0.15 * p0]
        if fl:
            notes.append(Msg(f"fluoropolymer-like peak at {fl[0]:.1f} eV (+{fl[0] - c:.1f} eV from C–C, e.g. Nafion "
                             "CF₂): insulating phase, differential charging possible — check against an internal "
                             "reference (lattice O 1s, metal line) before trusting the shift",
                             "ref_fluoro", x=f"{fl[0]:.1f}", d=f"{fl[0] - c:.1f}"))
    return Reference(c, w, float(snr), "low" if reasons else "high", reasons,
                     [round(float(x[i]), 2) for i, _ in good], notes)


def find_c1s_reference(x: np.ndarray, y: np.ndarray, ref: float = 284.8) -> float:
    """Position of the main C 1s (C–C/C–H) peak (uncorrected BE), see find_reference. Raises ValueError
    when there is no peak or the result has low confidence: the shift must then be set by hand."""
    r = find_reference(x, y, ref, fluoro_check=True)
    if r.confidence != "high":
        raise ValueError(f"C 1s at {r.position:.2f} eV: " + "; ".join(r.reasons))
    return r.position
