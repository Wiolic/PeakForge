# 1.0 acceptance checklist (another Windows computer)

> Purpose: show that the installer works on a **clean machine**. Any failed item blocks the `v1.0.0` tag.
> Tester: the user; fill each result into this file. Installer: `PeakForge-<version>-Setup.exe` from the Release workflow artifact.
> Status: **not verified** — the packaged program has only been run on the development machine.

Computer (fill in): Windows version ____  discrete GPU ____  antivirus ____  user name has non-ASCII characters ____

## 1. Install
- [ ] 1.1 Run Setup.exe **offline**, default location, no admin rights. SmartScreen "Windows protected your PC" → More info → Run anyway (unsigned; expected)
- [ ] 1.2 Start menu has PeakForge; the install folder has `examples\demo_fresh.csv` and `demo_aged.csv`
- [ ] 1.3 Antivirus (360 / Huorong / Defender) blocks or flags it? Name and what was done: ____
- [ ] 1.4 Install again into a path with spaces and non-ASCII characters (e.g. `D:\我的 软件\PeakForge`): starts and item 3 passes
- [ ] 1.5 With the "associate .xpsproj" task ticked, double-clicking a `.xpsproj` opens it in PeakForge

## 2. Start and interface
- [ ] 2.1 Double-click PeakForge.exe: main window opens, no console window, no error box
- [ ] 2.2 Language switch zh/en works; credit and disclaimer visible; About shows the version
- [ ] 2.3 Without a GPU driver / in a remote desktop the window renders normally (decides whether `opengl32sw.dll` can go)
- [ ] 2.4 Help → User guide (F1): all four pages open in both languages; formulas and figures render; dark theme readable; clicking a figure opens it
- [ ] 2.5 Help → Check for updates answers (up to date / newer / "could not reach GitHub")

## 3. Workflow with the demo data
- [ ] 3.1 New project, import `examples\demo_fresh.csv` (Ir 4f, O 1s, C 1s, Ti 2p appear)
- [ ] 3.2 Auto charge correction (C 1s) works; apply the Ir 4f preset; Fit; Fit all; progress bar and Cancel behave
- [ ] 3.3 O 1s generic model, 1 start: record O_lat centre ____ (reference 530.145 ± 0.05), FWHM ____ (1.329 ± 0.05), fractions ____ (43.9 / 41.3 / 14.8, ± 1)
- [ ] 3.4 Diagnostics (F6) runs; the quantification table shows its method note
- [ ] 3.5 Export PNG + Excel + Origin: PNG and xlsx written; the Origin step writes `build_origin.py` + `README_Origin.txt` (no originpro in the package); optional: run it in Origin with `run -pyf`
- [ ] 3.6 Import a table (CSV/Excel) through the column wizard; reopen the project and the results are still there

## 4. Command line, agents, diagnostics
- [ ] 4.1 `{install dir}\peakforge-cli.exe --version` and `selftest` (prints `selftest: ok`)
- [ ] 4.2 Agent → Connect writes `.mcp.json` pointing at `peakforge-cli.exe mcp`; an MCP client can list the tools
- [ ] 4.3 Help → Export diagnostics bundle: the zip has the log and versions and **no raw data**

## 5. Uninstall / upgrade
- [ ] 5.1 After uninstall, projects and `%USERPROFILE%\.peakforge\` (log, settings) are still there; the `.xpsproj` association is gone
- [ ] 5.2 Reinstall and install-over (old then new version) both work; settings kept

## Result
- Overall: pass / fail   Date: ____
- Failed items and symptoms:
