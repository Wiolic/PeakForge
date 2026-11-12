# Releasing (Windows)

1. `main` is green on CI; `CHANGELOG.md` has the release notes; `/code-review medium` done on the diff since the last release.
2. Bump `version` in `pyproject.toml` and `__version__` in `src/peakforge/__init__.py`; move "Unreleased" to the new version in
   `CHANGELOG.md`; commit ("Release x.y.z").
3. Local build (optional but recommended): `powershell -ExecutionPolicy Bypass -File packaging\build.ps1`
   (needs Python 3.12 and Inno Setup 6; creates `.venv-build`, runs pytest, builds, size guard, smoke test, installer, zip, SHA256SUMS).
4. Run the "Release" workflow manually (workflow_dispatch) and download the artifact `windows`.
5. Acceptance on another computer (preferably English Windows and a user name with non-ASCII characters): `packaging/ACCEPTANCE.md`.
   Any failed item blocks the tag.
6. Only after acceptance: `git tag vX.Y.Z && git push origin vX.Y.Z`. The workflow checks that the tag equals the package version,
   builds, and publishes Setup.exe, portable zip and SHA256SUMS.txt to the GitHub Release.
7. Check the Release page and that `peakforge update` on an older install reports the new version.

The size guard (`-LimitMB`, default 450) and the forbidden-package list live in `build.ps1` / `packaging/size_report.py`; when a
dependency grows, look at `build\size_report.csv` first. Before extending the `excludes` in `peakforge.spec`, run
`python packaging/used_modules.py` and check the package is not imported lazily.
