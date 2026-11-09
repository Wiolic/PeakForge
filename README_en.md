# PeakForge 锻峰

**XPS analysis desktop app**: read PHI `.spe` / VAMAS `.vms` / CSV / Excel → charge correction →
background → constrained peak fitting → fit diagnostics → one-click export to Origin (`.opju`),
publication figures and Excel. Use it fully by hand in the GUI, or let an AI agent
(Claude Code, Codex, Cursor…) drive it through **MCP**.

## Features

- **Readers**: PHI MultiPak/SmartSoft `.spe` (binary), VAMAS `.vms` (ISO 14976), CSV/TXT, Excel. SPE and VMS of the same acquisition give identical spectra (normalised to CPS).
- **Charge correction**: automatic C 1s C–C → 284.8 eV (configurable) or manual, per sample.
- **Backgrounds**: Shirley, Smart, linear, Tougaard (U3); draggable end points; automatic end points avoid neighbouring peak tails.
- **Line shapes** (unit area): Gaussian, Lorentzian, pseudo-Voigt, GL/SGL (CasaXPS notation), Voigt, Doniach–Šunjić ⊗ Gaussian, LA asymmetric.
- **Constraints**: bounds, fixing, expression links (`Ir4.fwhm`, `Ir0.center + 1.0`), spin–orbit doublets with tabulated splitting/area ratios for 51 core levels.
- **Presets**: C 1s adventitious, O 1s oxide, Ir 4f, Ta 4f, Pt 4f, Au 4f; save your own.
- **Diagnostics**: parameters at bounds, strong correlations, ΔBIC when removing each component, multi-start stability.
- **Batch**: reuse a model across samples (optionally freezing widths/shape), stacked comparison figures, quantification with editable RSFs.
- **Export**: Origin `.opju` built from the bundled Ir-new style template (plus 4 colour themes); without Origin, data + a script for `run -pyf`; PNG/TIFF/SVG/PDF; Excel.
- **Agent**: `peakforge mcp` exposes 20 MCP tools; the GUI reloads live when the agent edits the project.

## Install (Windows)

Install Python 3.11/3.12, download the ZIP from GitHub, extract, double-click `installer.py`.
Or anywhere: `pip install "git+https://github.com/Wiolic/PeakForge.git"` then `peakforge gui`.

## Agent

```bash
claude mcp add peakforge -- peakforge mcp
```

## Notes

Built-in RSFs are approximate Scofield values for rough quantification only — enter your
instrument's RSFs in the Quantification table. Presets are starting points; check the
diagnostics before reporting oxidation-state fractions.

MIT © Wiolic
