# Contributing

```bash
pip install -e ".[dev]"
python -m pytest -q                      # PEAKFORGE_TEST_DATA=<folder with .spe/.vms pairs> also checks readers on real data
ruff check src tests
ruff check --select ANN001,ANN201 src/peakforge/core
```

- Read `AGENTS.md` (conventions) and `ARCHITECTURE.md` first.
- Numerical change: write the failing test first, update `docs/METHODS.md` and `docs/METHODS_en.md`.
- User-visible text goes through `gui/i18n.py` (zh + en). Figures and exports are English.
- Never commit instrument data (`.spe`, `.vms`, `.opju`, projects) — see `.gitignore`.
- Moving code between files: `python tools/check_move.py ...` must report 0 problems.
- Releasing: `docs/dev/RELEASING.md`.
