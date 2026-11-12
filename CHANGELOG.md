# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/). "Method" entries change numbers; see `docs/METHODS_en.md`.

## [1.0.0] — 2026-11-13

### Added
- Windows installer and portable zip (PyInstaller onedir + Inno Setup): `PeakForge.exe` (GUI) and `peakforge-cli.exe`
  (command line and MCP: `peakforge-cli.exe mcp`). Per-user install, `.xpsproj` association, demo spectra in `examples\`.
- Help window (F1): GUI guide, beginner XPS fitting tutorial, XPS basics (Chinese and English).
- `peakforge update` and Help → Check for updates (queries the latest GitHub Release; sends nothing).
- `peakforge selftest`: checks an installation (GUI import, help pages, package data) offscreen.
- Reader plug-in registry, column templates for tables, project/model/preset validation, rotating log and diagnostics bundle.
- Cancellable background tasks with progress; fit/export workers never touch the project or widgets.
- Thermo Avantage reader (`.vgp` experiment + `.DATA` folder, or a single `.VGD`; standard library only).
- Colour palettes: base colours and combos, one base colour per element, per-figure base/mode (series or gradient);
  the same colours in the GUI, PNG/SVG/PDF, Excel (`Colours` sheet) and Origin.
- Export of a single figure (PNG/SVG/PDF/TIFF or one-graph Origin project): plot context menu, CLI `export --key`, MCP `export_figure`.
- Sourced 2p3/2 multiplet envelopes for Cr, Mn, Fe, Co and Ni (Biesinger et al. 2011), offered as presets and never applied automatically.

### Method (see METHODS)
- Tougaard universal cross section U2(1643) as default (the old 3-parameter default was wrong); U3 presets for Al/Si/polymers.
- χ²ᵣ uses an absolute noise estimate; acquisition time handled per format (PHI dwell, VAMAS c/s).
- Uncertainties: sandwich covariance, propagation to expression parameters, area ratios and fractions, background end-point noise.
- GL/SGL analytic and DS/LA fixed-grid line shapes: derivatives with respect to FWHM are now correct (were wrong by up to 10⁴× for some widths).
- Expressions are evaluated by an AST whitelist instead of `eval`.
- Charge correction: lowest-BE prominent peak near the reference (any region: C 1s, Au 4f, lattice O 1s), local fit,
  confidence checks (low-confidence results are not applied), fluoropolymer/F 1s warning, optional consistency checks.
- Fit-quality flags after every fit (width at the resolution/sampling floor, low S/N, noise-dominated residual,
  insignificant/outside/over-broad components, parameters at bounds, overlapping core levels); shown in red/orange.
- Automatic models: width floor from the instrument resolution and energy step, fewer components with a shared FWHM
  at low S/N, sub-level labels treated as doublets when the window covers both partners; RSF scaled for single sub-level scans.

### Known limitations
- Quantification uses approximate Scofield RSFs without transmission function, IMFP or angle corrections (stated in the UI and exports).
- Background uncertainty is not included in fit errors (Smart Shirley: about 1.2× underestimated).
- DS areas depend on the integration cut-off; Ir 4f with DS plus a pre-fixed Shirley background double counts the tail (tutorial, chapter 10).
- The packaged app is unsigned (SmartScreen / antivirus warnings are expected); acceptance-tested on a second computer (packaging/ACCEPTANCE.md).
