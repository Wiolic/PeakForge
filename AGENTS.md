# Developing PeakForge

- Package: `src/peakforge` (readers `io/`, fitting `core/`, `project.py`, `ops.py` shared by CLI / MCP / GUI,
  exports `export/`, GUI `gui/`, MCP `mcp_server.py`).
- Tests: `python -m pytest -q`; set `PEAKFORGE_TEST_DATA=<folder with .spe/.vms pairs>` to also check readers on real data.
- Never commit instrument data (.spe/.vms/.opju/projects) — see .gitignore.
- `export/origin_builder.py` must stay self-contained (only originpro + pandas): it is copied next to exported
  data and run inside Origin (`run -pyf`) when external originpro is not available.
- Every numerical method is documented in `docs/METHODS.md` / `docs/METHODS_en.md`; a change to
  `core/` numerics must update them and `tests/test_methods.py` (write the failing test first).
- File formats are readers in `io/registry.py` (`detect` + `read`); table column templates live in the
  project under "formats" (`io/table.py`, wizard back end `io/wizard.py`).
- Models, presets, templates and project files are checked by `schema.py` (error = crash or silently wrong,
  warning = unusual); swallowed exceptions are logged via `logs.log`, never `pass`.
- All text I/O names `encoding=` (enforced by `tests/test_encoding.py`).
- User-facing strings go through `gui/i18n.py` (zh/en). Figures and exports are English.
