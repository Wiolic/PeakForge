"""Peak line shapes. Every shape returns a profile with UNIT AREA, so the 'area' parameter of a
component is directly its integrated intensity.

Binding-energy convention: asymmetric tails extend towards HIGHER binding energy.

Shapes and their extra parameters:
  gaussian        -
  lorentzian      -
  pvoigt          eta   (0 = Gaussian, 1 = Lorentzian; linear sum)
  gl              m     (CasaXPS GL(p) product form, m = p/100, 0..1)
  sgl             m     (CasaXPS SGL(p) sum form)
  voigt           eta   (true Voigt; eta = Lorentzian share of the FWHM)
  ds              alpha (asymmetry, 0..0.5), gamma (Lorentzian FWHM, eV); 'fwhm' = Gaussian FWHM
  la              alpha, beta (LA tail exponents; smaller = longer tail), gw (Gaussian FWHM, eV)
"""
from __future__ import annotations

import numpy as np
from scipy.special import erfcx, voigt_profile

LN2 = np.log(2.0)

SHAPES: dict[str, dict] = {
    "gaussian": dict(extra={}, label="Gaussian"),
    "lorentzian": dict(extra={}, label="Lorentzian"),
    "pvoigt": dict(extra={"eta": (0.3, 0.0, 1.0)}, label="Pseudo-Voigt"),
    "gl": dict(extra={"m": (0.3, 0.0, 1.0)}, label="GL (product)"),
    "sgl": dict(extra={"m": (0.3, 0.0, 1.0)}, label="SGL (sum)"),
    "voigt": dict(extra={"eta": (0.3, 0.0, 0.99)}, label="Voigt"),
    "ds": dict(extra={"alpha": (0.1, 0.0, 0.45), "gamma": (0.3, 0.02, 2.0)},
               label="Doniach–Šunjić ⊗ Gauss"),
    "la": dict(extra={"alpha": (1.5, 0.5, 5.0), "beta": (2.0, 0.5, 8.0), "gw": (0.3, 0.0, 2.0)},
               label="LA (asym. Lorentzian ⊗ Gauss)"),
}


def _gauss(u, w):
    return np.sqrt(4 * LN2 / np.pi) / w * np.exp(-4 * LN2 * u ** 2 / w ** 2)


def _lor(u, w):
    return (2 / np.pi) * w / (4 * u ** 2 + w ** 2)


_GRID_N = 2049      # fixed point count: the grid then scales continuously with the widths, so the
                    # profile is a smooth function of every parameter (finite-difference Jacobians)


def _gl_area(m: float) -> float:
    """∫ exp(−a t²)/(1 + b t²) dt over ℝ (t = u/w), a = 4 ln2 (1−m), b = 4m:
    (π/√b)·erfcx(√(a/b)); limits m = 0 (Gaussian) and m = 1 (Lorentzian) included."""
    a, b = 4 * LN2 * (1 - m), 4 * m
    if b < 1e-12:
        return float(np.sqrt(np.pi / a))
    return float(np.pi / np.sqrt(b) * erfcx(np.sqrt(a / b)))


def _numeric_profile(shape: str, fwhm: float, a: float, b: float, c: float):
    """Unit-area DS / LA profile on a grid centred at 0 (u = x - centre, BE). Not cached on purpose:
    finite-difference Jacobians need exact (unrounded) parameter dependence. The range
    [−(8w+1), 25w+4] eV (w = largest width) defines the DS area (docs/METHODS.md); its point count is
    fixed, so the grid moves continuously with the widths."""
    w = max(fwhm, 1e-3)
    width = max(w, b if shape == "ds" else 0.0, c if shape == "la" else 0.0)
    span_hi = 25 * width + 4          # tail side (higher BE)
    span_lo = 8 * width + 1
    u = np.linspace(-span_lo, span_hi, _GRID_N)
    step = u[1] - u[0]
    if shape == "ds":
        alpha, gam = a, max(b, 1e-3) / 2.0
        # DS(ε) = cos[πα/2 + (1−α)·atan(ε/γ)] / (γ²+ε²)^((1−α)/2) has its tail at NEGATIVE ε
        # (ε = kinetic-energy offset). Higher BE = lower KE, so ε = −u puts the tail at higher BE.
        t = -u
        y = np.cos(np.pi * alpha / 2 + (1 - alpha) * np.arctan(t / gam)) / \
            (gam ** 2 + t ** 2) ** ((1 - alpha) / 2)
        y = np.clip(y, 0, None)
        y = _convolve_gauss(y, step, w)
    elif shape == "la":
        alpha, beta, gw = a, b, c
        lor = 1.0 / (1 + 4 * u ** 2 / w ** 2)
        y = np.where(u >= 0, lor ** alpha, lor ** beta)
        if gw > 1e-3:
            y = _convolve_gauss(y, step, gw)
    else:
        raise ValueError(shape)
    # cosine taper over the outer 10 % of each side, so the cut-off does not jump across data points
    # when a width changes (that made ∂/∂fwhm wrong by orders of magnitude)
    edge_lo, edge_hi = 0.1 * span_lo, 0.1 * span_hi
    tap = np.ones_like(u)
    lo_m, hi_m = u < -span_lo + edge_lo, u > span_hi - edge_hi
    tap[lo_m] = 0.5 - 0.5 * np.cos(np.pi * (u[lo_m] + span_lo) / edge_lo)
    tap[hi_m] = 0.5 - 0.5 * np.cos(np.pi * (span_hi - u[hi_m]) / edge_hi)
    y = y * tap
    area = np.trapezoid(y, u)
    return u, y / area if area > 0 else y


def _convolve_gauss(y, step, gw):
    if gw <= 1e-3:
        return y
    n = int(np.ceil(3 * gw / step))
    k_u = np.arange(-n, n + 1) * step
    k = np.exp(-4 * LN2 * k_u ** 2 / gw ** 2)
    return np.convolve(y, k / k.sum(), mode="same")


def profile(shape: str, x: np.ndarray, center: float, fwhm: float, **kw) -> np.ndarray:
    """Unit-area profile evaluated at x."""
    u = x - center
    w = max(float(fwhm), 1e-4)
    if shape == "gaussian":
        return _gauss(u, w)
    if shape == "lorentzian":
        return _lor(u, w)
    if shape == "pvoigt":
        eta = float(kw.get("eta", 0.3))
        return eta * _lor(u, w) + (1 - eta) * _gauss(u, w)
    if shape == "voigt":
        eta = min(max(float(kw.get("eta", 0.3)), 0.0), 0.99)
        fl = eta * w                          # Lorentzian FWHM
        # Olivero approximation inverted for Gaussian FWHM given total FWHM and fL
        fg2 = (w - 0.5346 * fl) ** 2 - 0.2166 * fl ** 2
        fg = np.sqrt(max(fg2, 1e-8))
        return voigt_profile(u, fg / (2 * np.sqrt(2 * LN2)), fl / 2)
    if shape == "gl":      # analytic, exactly normalised (no grid, no truncation)
        m = min(max(float(kw.get("m", 0.3)), 0.0), 1.0)
        t2 = (u / w) ** 2
        return np.exp(-4 * LN2 * (1 - m) * t2) / (1 + 4 * m * t2) / (w * _gl_area(m))
    if shape == "sgl":     # (1−m)·G + m·L, both peak-normalised, then unit area over ℝ
        m = min(max(float(kw.get("m", 0.3)), 0.0), 1.0)
        t2 = (u / w) ** 2
        area = w * ((1 - m) * np.sqrt(np.pi / (4 * LN2)) + m * np.pi / 2)
        return ((1 - m) * np.exp(-4 * LN2 * t2) + m / (1 + 4 * t2)) / area
    if shape == "ds":
        uu, yy = _numeric_profile(shape, w, float(kw.get("alpha", 0.1)), float(kw.get("gamma", 0.3)), 0.0)
    elif shape == "la":
        uu, yy = _numeric_profile(shape, w, float(kw.get("alpha", 1.5)), float(kw.get("beta", 2.0)),
                                  float(kw.get("gw", 0.3)))
    else:
        raise ValueError(f"unknown shape {shape}")
    return np.interp(u, uu, yy, left=0.0, right=0.0)


def apparent_fwhm(shape: str, fwhm: float, **kw) -> float:
    """Numerically measured FWHM of the profile (useful for DS / LA where 'fwhm' is not the FWHM)."""
    x = np.linspace(-20 * fwhm - 10, 20 * fwhm + 10, 40001)
    y = profile(shape, x, 0.0, fwhm, **kw)
    half = y.max() / 2
    idx = np.where(y >= half)[0]
    return float(x[idx[-1]] - x[idx[0]]) if len(idx) > 1 else float("nan")
