# Developing PeakForge

- Package: `src/peakforge` (readers `io/`, fitting `core/`, `project.py`, `ops.py` shared by CLI / MCP / GUI,
  exports `export/`, GUI `gui/`, MCP `mcp_server.py`).
- Tests: `python -m pytest -q`; set `PEAKFORGE_TEST_DATA=<folder with .spe/.vms pairs>` to also check readers on real data.
- Never commit instrument data (.spe/.vms/.opju/projects) — see .gitignore.
- `export/origin_builder.py` must stay self-contained (only originpro + pandas): it is copied next to exported
  data and run inside Origin (`run -pyf`) when external originpro is not available.
- User-facing strings go through `gui/i18n.py` (zh/en). Figures and exports are English.
