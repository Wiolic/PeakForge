"""Fit-quality flags computed after EVERY fit (cheap: no refits), for any element or core level.

Each flag is ``dict(level, code, args, text[, component])`` (text = English; the GUI translates by code
with the pre-formatted ``args``); level 'error' = the result is probably wrong
(shown in red, not silently reported), 'warning' = check before using it. See docs/METHODS.md §5.
"""
from __future__ import annotations

from typing import Any

import numpy as np

# Narrowest instrumental width of a laboratory spectrometer: Ag 3d5/2 FWHM 0.47 eV at 10 eV pass energy
# (monochromatic Al Kα, Kratos Axis Ultra; Biesinger et al., Appl. Surf. Sci. 257 (2011) 2717, section 2).
# A fitted core-line component cannot be narrower than this; 0.5 eV is used as the floor.
MIN_FWHM_INSTRUMENT = 0.5
MIN_POINTS_PER_FWHM = 2.5     # a component narrower than ~2.5 data points is not resolved by the sampling
LOW_SNR = 30.0                # peak height / point noise below which χ²ᵣ cannot tell models apart
NOISE_DOMINATED_RMS = 10.0    # % of peak height
BROAD_FWHM = 2.5              # eV, and ≥ 2.5× the narrowest component, holding > 30 % of the area


def resolution_floor(x: np.ndarray) -> float:
    """Lower bound for a fitted FWHM (eV): instrument floor or sampling limit, whichever is larger."""
    x = np.asarray(x, float)
    step = float(np.median(np.abs(np.diff(x)))) if len(x) > 1 else 0.0
    return max(MIN_FWHM_INSTRUMENT, MIN_POINTS_PER_FWHM * step)


def _point_noise(y: np.ndarray) -> float:
    d = np.diff(np.asarray(y, float), 2)
    if len(d) == 0:
        return float("nan")
    return float(1.4826 * np.median(np.abs(d - np.median(d))) / np.sqrt(6.0))


def peak_snr(x: np.ndarray, y: np.ndarray, bg: np.ndarray, sigma: np.ndarray | None = None) -> float:
    """Height of the strongest feature above the background divided by the point noise there
    (counting noise when known, else a robust estimate from second differences)."""
    s = np.asarray(y, float) - np.asarray(bg, float)
    if len(s) == 0:
        return float("nan")
    i = int(np.argmax(s))
    noise = float(sigma[i]) if sigma is not None and np.isfinite(sigma[i]) and sigma[i] > 0 else _point_noise(y)
    return float(s[i] / noise) if noise and np.isfinite(noise) and noise > 0 else float("inf")


def quality(model: Any, prep: Any, res: Any) -> list[dict]:
    """Flags for a fitted model (model: RegionModel, prep: Prepared, res: FitResult)."""
    flags: list[dict] = []
    if len(res.x) < 3:
        return flags
    floor = resolution_floor(res.x)
    lo, hi = float(np.min(res.x)), float(np.max(res.x))
    snr = peak_snr(res.x, res.y, res.bg, getattr(prep, "sigma", None))
    if np.isfinite(snr) and snr < LOW_SNR:
        flags.append(dict(level="warning", code="low_snr", args=dict(snr=f"{snr:.0f}"),
                          text=f"Low S/N ({snr:.0f}): χ²ᵣ ≈ 1 does not validate the model at this noise level; "
                               "keep few components, share widths, and fix what the chemistry fixes"))
    if res.chi2_red < 2 and res.rms_pct > NOISE_DOMINATED_RMS:
        flags.append(dict(level="error", code="noise_dominated",
                          args=dict(rms=f"{res.rms_pct:.0f}", chi2=f"{res.chi2_red:.2f}"),
                          text=f"Residual RMS {res.rms_pct:.0f} % of the peak height while χ²ᵣ = {res.chi2_red:.2f}: "
                               "the data cannot distinguish models — component positions and fractions are not "
                               "determined"))
    in_tot = [c for c in model.components if c.in_total]
    widths = [res.values[c.name]["fwhm"] for c in in_tot if "fwhm" in res.values.get(c.name, {})]
    narrowest = min(widths) if widths else float("nan")
    reported: set[str] = set()      # parameters already explained by a component flag (not repeated as 'bound')
    for c in model.components:
        v = res.values.get(c.name, {})
        p = c.params.get("fwhm")
        free_w = p is not None and (p.vary or bool(p.expr))
        if free_w and "fwhm" in v and v["fwhm"] <= floor * 1.02:
            reported.add(f"{c.name}.fwhm")
            flags.append(dict(level="error", code="narrow", component=c.name,
                              args=dict(c=c.label or c.name, w=f"{v['fwhm']:.2f}", floor=f"{floor:.2f}"),
                              text=f"{c.label or c.name}: FWHM {v['fwhm']:.2f} eV at the resolution/sampling limit "
                                   f"({floor:.2f} eV) — probably fitting noise, not a peak"))
        if "center" in v and not lo <= v["center"] <= hi:
            flags.append(dict(level="error", code="outside", component=c.name,
                              args=dict(c=c.label or c.name, x=f"{v['center']:.2f}", lo=f"{lo:.1f}", hi=f"{hi:.1f}"),
                              text=f"{c.label or c.name}: centre {v['center']:.2f} eV outside the fitted window "
                                   f"{lo:.1f}–{hi:.1f} eV"))
        if not c.in_total:
            continue
        a = res.areas.get(c.name, 0.0)
        err = res.stderr.get(f"{c.name}.total_area")
        if a <= 0 or (err is not None and np.isfinite(err) and a < 2 * err):
            reported.add(f"{c.name}.area")
            flags.append(dict(level="warning", code="insignificant", component=c.name,
                              args=dict(c=c.label or c.name, a=f"{a:.3g}"),
                              text=f"{c.label or c.name}: area {a:.3g} not significant (< 2σ) — the data do not "
                                   "support this component"))
        f = res.fractions.get(c.name, 0.0)
        if ("fwhm" in v and v["fwhm"] > BROAD_FWHM and np.isfinite(narrowest) and v["fwhm"] > 2.5 * narrowest
                and f > 30):
            flags.append(dict(level="warning", code="broad", component=c.name,
                              args=dict(c=c.label or c.name, w=f"{v['fwhm']:.1f}", f=f"{f:.0f}"),
                              text=f"{c.label or c.name}: {v['fwhm']:.1f} eV wide with {f:.0f} % of the area — may be "
                                   "absorbing background, a loss feature or the tail of an asymmetric line "
                                   "(metals and conducting oxides need an asymmetric line shape)"))
    hits = [h for h in res.bound_hits if h.split(" ")[0] not in reported]
    if hits:
        flags.append(dict(level="warning", code="bound", args=dict(hits=", ".join(hits)),
                          text="Parameters at their bounds (the data push past the allowed range — check the "
                               "bounds or the model): " + ", ".join(hits)))
    if res.noise == "counting" and np.isfinite(res.noise_ratio) and not 0.5 < res.noise_ratio < 2.0:
        flags.append(dict(level="warning", code="noise_ratio", args=dict(r=f"{res.noise_ratio:.1f}"),
                          text=f"Data noise is {res.noise_ratio:.1f}× the counting-statistics variance expected "
                               "from the acquisition time — χ²ᵣ and weights are unreliable"))
    return flags


def has_errors(flags: list[dict]) -> bool:
    return any(f.get("level") == "error" for f in flags)
