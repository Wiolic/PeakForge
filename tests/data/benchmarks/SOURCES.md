# Benchmark data sources (phase 1 — status 2026-11-12)

Rule: every benchmark records URL, licence, citation and which table/page the reference values come from;
data with unclear licence is NOT copied into the repository (local-only tests under `tests/local/`, which is
git-ignored, read them from a folder given by an environment variable).

## Used

| Data | Licence | Where | What is checked |
|---|---|---|---|
| Analytic forms / scipy | — | `tests/benchmark/test_synthetic.py` | SGL closed form, Voigt vs `scipy.special.voigt_profile`, Shirley fixed point, recovery statistics (z-scores vs reported 1σ) |
| **SASJ VAMAS/TWA2/A9 test spectra** — https://sasj.jp/TestSpectra/TestSpectra.html (Excel/CSV set). M. Suzuki, S. Fukushima, S. Tanuma, *J. Surf. Anal.* 14 (2007) 104–117, section 3 and Fig. 1 | **none stated** (page: free download for testing software) → local only | `tests/local/test_sasj.py`, `PEAKFORGE_SASJ=<…/EXCEL_TEXT_FORMAT>` | Measured Au, Ag, Cu (monochromatic Al Kα), 1200→0 eV, 0.5 eV step, counts. Mixtures b001 = Au+Ag+Cu, b002 = Au+0.1Ag+0.01Cu, b003 = Au+0.01Ag+0.001Cu (paper, section 3) → exactly invertible to pure spectra. Checks: area independent of the other elements where they add < 2 % structure; 5 noise realisations per amplitude unbiased vs the parent, reported 1σ ≥ scatter. No true peak parameters are published (the set was made for peak *detection*). |
| **Zenodo 6672033** — E. Quérel, "Data access - Operando characterization and theoretical modelling of metal\|electrolyte interphase growth kinetics in solid-state-batteries - part I: experiments" (Imperial College London), zip md5 c333e487123485ad6d79899849464d87 | **CC BY 4.0** (kept local anyway: data are large and not ours) | `tests/local/test_zenodo_casa.py`, `PEAKFORGE_CASA_ZENODO=<…/Data access/XPS>` | 5 VAMAS files, 112 blocks, 86 Shirley regions with CasaXPS models (Na 1s, P 2p, Si 2p, Zr 3d; LA line shapes, area/width/position links). PeakForge refits each model under the same region, end-point averaging and links (its own LA, α/β from CasaXPS, Gaussian width free — CasaXPS's LA `m` is undocumented in accessible sources). Asserted: CasaXPS areas are cps·eV (Σ areas / Shirley integral median 1.013); all 61 regions with one free component agree — position ≤ 0.19 eV (median 0.007), area \|z\| < 1.6 against PeakForge's 1σ, median area ratio 0.991. Overlapping multi-component partitions differ (translation of FWHM bounds; reported only). |

Observations from the SASJ data (recorded in docs/METHODS.md):
- the noise copies are the parent scaled by c (0.0045–0.29) plus noise of 1.1–1.3× Poisson, integer counts;
- areas in the mixtures deviate 5–40 % where another element adds a sloped or structured background
  (Cu 3p under Au 4f; Au 4d losses under a weak Ag 3d) — a background-model limitation, not a code error;
- fitted spin–orbit splits (free): Au 4f 3.66–3.67, Ag 3d 6.01, Cu 2p 19.79–19.80 eV; on these metal spectra
  the LA shape gives the lowest BIC for Au and Ag (asymmetric metallic lines), as expected.

## Searched, not used (yet)

| Candidate | Finding | Next step |
|---|---|---|
| Seah & Brown 1998, *J. Electron Spectrosc. Relat. Phenom.* 95, 71 (doi 10.1016/S0368-2048(98)00204-7): synthetic VAMAS test spectra with known parameters | NPL repository (eprintspublications.npl.co.uk/1533): "Full text not available"; no files online | ask NPL / the authors |
| Zenodo 7074887 — D. Morgan, "Revisiting Degradation in the XPS Analysis of Polymers", SIA doi 10.1002/sia.7151 | CC BY 4.0; one zip 6.9 MB; VAMAS, CasaXPS ≥ 2.3.24 recommended; fits not stated | check for fit models after download |
| Zenodo 17221867 — "XPS", one .vms (399 kB) | CC BY 4.0; no description | low priority |
| Zenodo 10027319 — VAMAS TWA2 project 33 (graphene) interlaboratory data | Excel raw data + protocol, no fits | possible reader / quantification check |
| surfacespectra.com/xps/examples (curve-fitted PET, Fomblin Y, VAMAS) | licence not stated | ask / skip |
| ISO 15472 reference energies (Au 4f7/2 83.96, Ag 3d5/2 368.21, Cu 2p3/2 932.62 eV) | seen only in secondary sources | cite from the standard or NPL before using as test values |
| Figshare "Raw data of XPS fitting" | not found under that title | need a link |
| Tougaard universal cross section | C = 1643 eV² confirmed; phase 0 used Tougaard SIA 2024 (doi 10.1002/sia.7273) | covered by `tests/test_methods.py` |
