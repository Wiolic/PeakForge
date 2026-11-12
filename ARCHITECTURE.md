# Architecture

PeakForge is one Python package (`src/peakforge`). The GUI, the command line and the MCP server are thin front ends over the
same functions, so a result is the same whichever way it was produced.

```
io/        readers (registry.py: detect + read per format), table column templates (table.py), wizard back end (wizard.py)
core/      numerics only, no I/O: lineshapes, background, model (parameters, expressions), fit, diagnostics, quant
project.py project folder + .xpsproj (JSON): spectra, samples, charge shifts, models, results; fit_inputs / store_fit
ops.py     the operations shared by CLI / MCP / GUI (import, charge, preset, fit, batch, quantify, export ...)
schema.py  validation of projects, models, presets, templates (error = crash or silently wrong, warning = unusual)
export/    PNG (Figure API), Excel, Origin (origin_builder.py is self-contained, runs inside Origin without PeakForge)
gui/       main_window.py + window/ mixins, model panel, canvas, help window (help.py), i18n (zh/en), tasks.py (QThread)
tasks.py   TaskHandle / Cancelled (cancellation and progress, no Qt)
cli.py, mcp_server.py, agent.py, update.py, logs.py, selftest.py
docs/      help documents shipped with the app (md + images); repo-level docs/METHODS*.md describe every numerical method
```

Rules that matter
- **Threads**: a worker never touches widgets or the `Project`. Inputs are copied in the UI thread
  (`Project.fit_inputs`, `exporter.collect_export`); the result is written back in `on_done` and dropped if the project or model
  changed meanwhile. matplotlib is used through `Figure` only, never pyplot. `Cancelled` is a `BaseException`.
- **Numerics**: any change in `core/` updates `docs/METHODS*.md` and `tests/test_methods.py` (failing test first).
- **Text I/O** always names `encoding=` (`tests/test_encoding.py`).
- **Packaging** (`packaging/`): PyInstaller onedir with two executables; `smoke.py` runs the packaged program
  (selftest, a fit against reference values, exports, MCP handshake). The packaged app has no originpro, so Origin export
  writes data + `build_origin.py` for `run -pyf` inside Origin.
