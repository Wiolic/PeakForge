# PeakForge — methods

[中文](METHODS.md)

This page states exactly what PeakForge computes, with references and known limitations. Each statement
marked **[test]** is pinned by a regression test in `tests/test_methods.py`. Code: `src/peakforge/core/`.

## 1. Conventions
- Binding energy (BE) ascending internally, intensity in counts per second (cps).
- Asymmetric tails extend to **higher BE** (lower kinetic energy).
- Every line shape has **unit area**: a component's `area` is its integrated intensity. For a spin–orbit
  doublet `area` is the main (high-j) line; the partner has `area·ratio` at `center + split`.
  Reported areas, area errors, fractions and at% always use the **total** doublet area.

## 2. Line shapes (`lineshapes.py`)
| Name | Definition | What `fwhm` means |
|---|---|---|
| `gaussian`, `lorentzian` | standard | true FWHM |
| `pvoigt` | η·L + (1−η)·G, both unit-area, same FWHM | true FWHM |
| `voigt` | scipy `voigt_profile`; Gaussian width from the Olivero–Longbothum relation f_V ≈ 0.5346 f_L + √(0.2166 f_L² + f_G²) with f_L = η·f_V | true FWHM (relation accurate to ≈0.02 %) |
| `gl` | CasaXPS GL(p) **product** exp[−4 ln2 (1−m) u²/w²] / (1 + 4m u²/w²), m = p/100 | **not** the FWHM for 0 < m < 1 (GL(30): 4 % narrower). The measured width is reported as *Apparent FWHM* **[test]** |
| `sgl` | CasaXPS SGL(p) **sum** (1−m)·G + m·L with peak-normalised G and L | true FWHM |
| `ds` | Doniach–Šunjić cos[πα/2 + (1−α) arctan(ε/γ)] / (γ² + ε²)^((1−α)/2), ε = −(BE − center), convolved with a Gaussian | Gaussian FWHM; Lorentzian width is `gamma` |
| `la` | asymmetric Lorentzian: L^α on the high-BE side, L^β on the low-BE side, convolved with a Gaussian of FWHM `gw` (eV) | Lorentzian FWHM |

Limitations:
- **DS area depends on the integration range.** For α > 0 the DS integral diverges, so the profile is
  normalised on [center − (8w+1), center + (25w+4)] eV (w = largest width), with a cosine taper over the
  outer 10 % of each side, and is zero outside. "Area"
  and fractions of DS components therefore mean "area inside that range". This is the same kind of
  convention as in other programs but **not numerically identical** to them; compare DS areas only within
  PeakForge.
- **LA parameters are not CasaXPS LA(α, β, m) parameters.** CasaXPS gives the Gaussian width `m` in data
  channels; PeakForge's `gw` is in eV. Shapes can be matched, but parameter values cannot be copied across.
- `gl` and `sgl` are evaluated analytically and normalised over ℝ: GL area = w·(π/√b)·erfcx(√(a/b)),
  a = 4 ln2 (1−m), b = 4m; SGL area = w·[(1−m)√(π/4 ln2) + m·π/2] **[test]**.
- Asymmetric shapes (ds, la) are computed on a grid of 2049 points spanning the range above (step ≈ w/40)
  and interpolated; the fixed point count and the taper make the profile a smooth function of all
  parameters, which the finite-difference Jacobian (and so every reported error) relies on **[test]**.
- **Fixed in phase 1:** GL, SGL, DS and LA used a grid whose point count jumped with the width (step
  min(0.02, w/15)), and DS/LA were cut off abruptly at the range edge. ∂profile/∂fwhm was then wrong for
  20–45 % of widths, by up to 10⁴× — e.g. an SGL fit reported FWHM ± 7·10⁻⁸ eV. Fitted values were barely
  affected; errors and convergence were. SGL areas were normalised on the truncated grid (Lorentzian part
  ≈2 % short at w = 1 eV); now over ℝ like `lorentzian` and `pvoigt`.

## 3. Backgrounds (`background.py`)
End-point intensities are averaged over `avg` eV (default 0.5) inside the background limits; outside the
limits the background stays at the end values.
- **linear**: straight line between the averaged end points.
- **shirley**: iterative Shirley (Shirley 1972; Proctor & Sherwood 1982). B(E) = y_lo + (y_hi − y_lo)·
  ∫_lo^E [y − B] / ∫_lo^hi [y − B], iterated to convergence.
- **smart**: Shirley with B ≤ data at every iteration (as in CasaXPS "Smart").
- **tougaard**: B(E) = ∫_{E'<E} K(E − E') [y(E') − y_lo] dE' with
  K(T) = B·T / [(C − T²)² + D·T²] (three-parameter U3; Tougaard 1997, Tougaard 2024 eq. 2).
  The default is the **universal two-parameter U2(1643)**, K = B·T / (C + T²)², C = 1643 eV² (Tougaard
  1989; Tougaard 2024 eq. 1), recommended for transition metals, their alloys and oxides. U2 is written as
  U3 with D = 4C (algebraically identical) **[test]**. Literature presets for materials with a sharp plasmon:
  U3 Al (C, D) = (230, 4.5), Si (325, 96), polymer (551, 436) eV² **[test]**.
  - B is **not** used as given: the background is rescaled so that it meets the averaged high-BE end point
    (the common practical choice in peak-fitting programs; QUASES-type analysis fixes B by normalisation
    instead).
  - No band-gap onset Θ(T − E_g); a uniform energy grid is assumed.
  - **Fixed in 0.1.x:** PeakForge 0.1 used (B, C, D) = (2866, 1643, 1) in the U3 formula, which is neither
    U2 nor a published U3 and has a near-pole at T ≈ 40 eV. Models saved with that value are migrated to
    U2 on loading **[test]**.
- The background is computed **before** the peak fit and held fixed. The noise of its two end-point averages
  is propagated into the reported errors (section 5); the choice of background type and end points is not.
- **Limitation (SASJ test spectra, phase 1):** a Shirley/Tougaard background assumes the step comes from the
  fitted peaks. A falling or structured background from *another* signal (Cu 3p tail under Au 4f, Au 4d loss
  structure under a weak Ag 3d) biases areas by 5–40 % with every background type offered. Choose the
  window and end points so that foreign structure is small, or model it with an extra component.

## 4. Noise model, weighting and χ²ᵣ (`fit.py`)
**Acquisition time.** Counts are N = cps · t, where t is the effective acquisition time per point:
| Format | t | Evidence |
|---|---|---|
| VAMAS (ISO 14976) | dwell × number of scans; ordinate divided by t unless its unit is c/s | standard |
| PHI .spe | dwell (**not** dwell × sweeps) | on PHI Genesis data the point-to-point variance of the stored cps equals that expected for cps·dwell: variance ratio 0.65–1.52 (mean ≈1.0) over 10 narrow regions of two samples (C 1s, O 1s, K 2p, Ir 4f with 3 sweeps, Ta 4f with 5) and 0.82–1.04 for three surveys, with the 4th-difference estimator below (re-checked in phase 1); it would be 2–5 for cps·dwell·sweeps |
| CSV / Excel, automatic | unknown → estimated from the data | — |
| CSV / Excel with a column template, `intensity: cps` | `acq_time` if given, else estimated | user declaration |
| CSV / Excel with a column template, `intensity: counts` | `acq_time` t if given (cps = counts / t), else t = 1 s (cps = counts, so N is exact) | user declaration **[test]** |

**Noise σᵢ.** With known t: σᵢ = √(yᵢ·t)/t (Poisson, data variance). Without: σᵢ² = k·yᵢ. Before the fit k
is estimated from second differences of the data (only the shape of σ matters for the weights). **After
the fit** k is re-estimated from 4th differences of the residual, dᵢ = rᵢ₋₂ − 4rᵢ₋₁ + 6rᵢ − 4rᵢ₊₁ + rᵢ₊₂
(var = 70 σ² for white noise), k = median(dᵢ²/70·envᵢ)/0.455 · n/(n − n_free) (variance ∝ intensity; for
zero-centred, background-subtracted data the constant-variance model chosen before the fit is kept **[test]**); this k gives χ²ᵣ for tables
and the data/counting noise ratio when t is known **[test]**. The fitted model removes the peaks and the
4th difference removes smooth misfit, so the estimate stays unbiased when peaks fill the window or the
step is coarse (0.05–0.5 eV steps, FWHM 0.6–1.2 eV: within ±15 %). Scatter ≈ ±15–20 % for 150–300 points.
Outside 0.5–2 the diagnostics warn that the acquisition parameters do not describe the noise; with
χ²ᵣ ≫ 1 at coarse steps the excess can instead be point-to-point line-shape misfit (the warning says so).
- **Fixed in phase 1:** the pre-fit second-difference median was inflated by peak curvature whenever peaks
  cover a sizeable part of the window: ×2–3 at 0.1 eV and ×50 at 0.5 eV steps for an Au 4f-like window
  (median of a mixture of noise and curvature points), so χ²ᵣ of tables came out too low by that factor.

**Weighting.** `none`: ordinary least squares. `poisson`: residuals weighted by 1/σᵢ (relative weights
only, so the solution does not depend on t).

**χ²ᵣ** = Σ(residualᵢ/σᵢ)² / (n − n_free), **whatever the weighting** **[test]**. ≈1 means the misfit is at
noise level. With an estimated noise level it is shown as "≈". The background is fixed, so the noise of
its end-point averages also enters χ²ᵣ: with only 2–3 points per end average (coarse steps) χ²ᵣ ≈ 1.5 is
expected even for the true peak model. High-count spectra often give χ²ᵣ ≫ 1 even
at RMS < 1 %: the model is then statistically incomplete (line shape, background) although it may be
adequate for the question asked.
- **Fixed in 0.1.x:** 0.1 normalised the Poisson weights before computing χ², and without weighting used
  std(Δy)/√2 as noise, which includes the slope of peaks (χ²ᵣ far below 1). Fitted values were not affected.

## 5. Uncertainties
- Covariance of free parameters: linear propagation of the data noise, Δp = A·Jᵀ·W·(I − G)·Δy, i.e. the
  **sandwich** A·M Σ Mᵀ·A with M = Jᵀ·W·(I − G), A = (JᵀJ)⁻¹, Σ = diag(σᵢ² · χ²ᵣ), W = diag(wᵢ), J = Jacobian of
  the weighted residuals at the solution. G = ∂background/∂y: the background is computed from the same noisy
  data, mainly through its two end-point averages, so G = Σ_ends g·uᵀ (u = averaging weights, g = response
  of the background to that average, by finite difference). The full ∂bg/∂y differs by < 3 % (Shirley,
  Smart, Tougaard, linear). Scaling by χ²ᵣ absorbs misfit and the scale of an estimated noise level. Without
  a noise model: A·s², s² = RSS/dof.
  On Poisson data the reported 1σ agree with the scatter over noise realisations to ≈10 % for weighted and
  unweighted fits **[test]** (0.1 used A·s², which under-estimated errors ≈1.7× for unweighted fits).
- Derived quantities — expression-linked parameters, total doublet area, % fractions — by linear
  propagation with a numerical gradient **[test]**.
- **Fixed in phase 1:** without G the area 1σ was 1.6–2.8× too small with a Shirley background (40–150 noise
  realisations, 0.5–2 eV end averages) **[test]**. Smart Shirley still under-estimates ≈1.2×: its clip inside
  the iteration adds a dependence on interior points that G does not cover.
- With systematic misfit (χ²ᵣ ≫ 1) the χ²ᵣ scaling makes the 1σ larger than the noise-only scatter (SASJ
  metal spectra at 0.5 eV steps: centre 5–15×, area ≈2×). This is deliberate: the reported error then
  includes lack of fit.
- Not included: choice of background type and end points, line-shape choice. Errors of parameters at
  a bound are not meaningful (they are listed under "At bounds").

## 6. Model comparison and stability (`diagnostics.py`)
- AIC = n ln(RSS/n) + 2k, BIC = n ln(RSS/n) + k ln n (weighted RSS; Gaussian-likelihood approximation).
- **ΔBIC on removal**: each component is removed and the rest refitted. ΔBIC > 10 strong, 2–10 positive,
  < 2 not supported (a coarsening of Kass & Raftery 1995: 2–6 positive, 6–10 strong, > 10 very strong). If the reduced model fits better the full fit is in a
  local minimum. ΔBIC assumes residuals at noise level; with systematic misfit (χ²ᵣ ≫ 1) it overstates the
  evidence for extra components.
- **Multi-start stability**: up to 12 random starts; solutions within 2 % of the best cost are compared; a
  fraction spread > 3 % is reported.
- Parameters correlated with |r| > 0.95 are reported.

## 7. Charge correction (`quant.find_c1s_reference`)
Shirley background, then a single GL(30) fitted to the low-BE side and top of the strongest peak inside
283–287 eV (uncorrected BE); the shift moves it to the reference (default 284.8 eV, project setting).
The search **refuses** (shift left unchanged, sample reported) when the maximum lies within 0.3 eV of the
window edge, there is no clear peak, or the fit wanders > 0.95 eV **[test]**. Adventitious-carbon
referencing is itself uncertain by several tenths of an eV and can fail on some samples (Greczynski &
Hultman 2020); use an internal reference where possible.

## 8. Quantification (`quant.py`)
at%ᵢ = (Aᵢ/RSFᵢ) / Σⱼ(Aⱼ/RSFⱼ), A = total fitted area (or background-subtracted integral). Built-in RSFs are
approximate Scofield (1976) cross sections for Al Kα normalised to C 1s = 1, **without** analyser
transmission, IMFP or angular-asymmetry corrections: absolute at% can be off by tens of percent. Enter the
RSFs of your instrument (they include those factors) for quantitative work. This note is printed in the
GUI and in the Excel export.

## 9. Parameter expressions
Expressions such as `Ir0.center + 1.1`, `O_lat.fwhm`, `max(A.center, 3) - sqrt(4)` are parsed into a
syntax tree and evaluated without Python `eval`: numbers, `+ − × / **`, unary ±, `abs min max sqrt exp
log`, `pi` and `component.param` references only; anything else is rejected **[test]**.
Models are validated when they are loaded or set (`schema.py`, also `peakforge validate`): references to
missing components/parameters, circular expressions, min > max, free parameters that neither the line
shape nor any expression uses (the fit cannot determine them — usually a typo), unknown shapes or
backgrounds and fit ranges outside the data are **errors** and the model is refused; start values outside
their bounds, a spin–orbit area ratio fixed > 5 % away from the (2j+1) value of the orbital table, a split
fixed > max(0.3 eV, 10 %) away from the table, and more than one free parameter per 3 points are
**warnings** **[test]**. Auxiliary parameters (e.g. `Ir3.shift` used in `Ir0.center + Ir3.shift`) are allowed.

**Cancellation (background tasks).** `fit(..., check=…)` calls a read-only cancellation point at every residual evaluation; the diagnostics' `progress/check` only report. Neither changes any number (`tests/test_methods.py::test_cancel_hooks_…` compares bit by bit); a cancel raises `Cancelled` and the project is left untouched.

## 10. Validation status
| Area | Status |
|---|---|
| Unit area, tail direction, recovery of synthetic parameters, Shirley monotonicity, every core level Li–U | tested (`test_core.py`, `test_all_elements.py`) |
| Tougaard kernel vs direct integral, U2/U3 forms and presets | tested (`test_methods.py`) |
| χ²ᵣ ≈ 1, error calibration, safe expressions, charge-reference failure modes | tested (`test_methods.py`) |
| SPE = VMS for the same acquisition | tested on local data only (`PEAKFORGE_TEST_DATA`) |
| Closed forms / independent implementations: SGL formula, Voigt vs scipy, Shirley fixed point, recovery statistics over 20 seeds | tested (`tests/benchmark/`) |
| Error calibration with a computed Shirley background; noise level with peaks filling the window | tested (`test_methods.py`) |
| SASJ VAMAS/TWA2/A9 test spectra (measured Au/Ag/Cu; Suzuki, Fukushima, Tanuma, J. Surf. Anal. 14 (2007) 104): composition inversion, area independence of other elements, unbiased results and error ≥ scatter over noise realisations | local only (no redistribution terms; `tests/local/test_sasj.py`, `PEAKFORGE_SASJ`) |
| CasaXPS models stored in public data (Zenodo 6672033, CC BY 4.0: 86 regions Na 1s/P 2p/Si 2p/Zr 3d): area units, and all 61 single-component regions refitted under the same constraints — positions ≤ 0.19 eV, areas within 1.6σ, median area ratio 0.991 | local only (`tests/local/test_zenodo_casa.py`, `PEAKFORGE_CASA_ZENODO`) |
| Seah & Brown 1998 VAMAS test spectra; published fits of open data sets; ISO 15472 energies | not available / not yet verified (`tests/data/benchmarks/SOURCES.md`) |
| Comparison with CasaXPS / Avantage on the same spectra | not yet done |

## References
- D. A. Shirley, Phys. Rev. B 5 (1972) 4709.
- A. Proctor, P. M. A. Sherwood, Anal. Chem. 54 (1982) 13.
- S. Doniach, M. Šunjić, J. Phys. C 3 (1970) 285.
- S. Tougaard, Surf. Sci. 216 (1989) 343 (universal cross section).
- S. Tougaard, Surf. Interface Anal. 25 (1997) 137 (universality classes, U3).
- S. Tougaard, Surf. Interface Anal. (2024), doi:10.1002/sia.7273 (eqs. 1–2; U3 parameters for Al, Si, polymers).
- J. J. Olivero, R. L. Longbothum, J. Quant. Spectrosc. Radiat. Transfer 17 (1977) 233.
- J. H. Scofield, J. Electron Spectrosc. Relat. Phenom. 8 (1976) 129.
- R. E. Kass, A. E. Raftery, J. Am. Stat. Assoc. 90 (1995) 773.
- G. Greczynski, L. Hultman, Prog. Mater. Sci. 107 (2020) 100591.
- ISO 14976:1998, Surface chemical analysis — Data transfer format (VAMAS).
- CasaXPS manual (GL, SGL, LA line-shape definitions).
