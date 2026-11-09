# PeakForge Quickstart

> For materials scientists, chemists and physicists with basic XPS knowledge and **no programming or command-line experience**. Mouse only — or hand the whole analysis to an AI.
> **Developed by Eggy & Claude Opus 5.5** · [中文](QUICKSTART.md) · [README](README_en.md)

## Step 0: install (once)

1. Install **Python 3.12** from <https://www.python.org/downloads/> and tick **“Add python.exe to PATH”**.
2. At <https://github.com/Wiolic/PeakForge> click **Code → Download ZIP**, unzip anywhere.
3. Double-click **`installer.py`** (if it opens in an editor: right-click → *Open with* → *Python*). Click **Install** and wait. Keep “install originpro” ticked if Origin 2021+ is installed.
4. Start PeakForge from the desktop icon or by double-clicking a `.xpsproj` file. The first start shows the disclaimer: **cross-check results with CasaXPS / Avantage / MultiPak before publishing.**

## Route A: mouse only

Practice data: `examples/demo_fresh.csv`, `examples/demo_aged.csv` (synthetic C 1s, O 1s, Ir 4f, Ti 2p).

1. **File → New project** — pick an empty folder.
2. **Import data** — `.spe` / `.vms` / `.csv` / `.xlsx` (raw files are copied read-only).
3. **Auto charge correction** — C 1s C–C → 284.8 eV; right-click a sample to set a shift by hand.
4. Click a region on the left. Dot colours: grey = no model, amber = changed but not refitted, green = fitted.
5. **Preset**: a matching preset (C 1s, O 1s, Ir/Ta/Pt/Au 4f), or **“Generic: automatic peak search (any element)”** for any element Li–U → **Apply**.
6. **Fit** (F5).
7. Adjust: drag a component's coloured dot; right-click → add peak / remove component / background ends; drag the dashed lines; edit value/min/max, untick *Vary* to fix, type `Ir4.fwhm` in *Link expr* to share widths; `Ctrl+Z` undoes. Fit again.
8. **Diagnostics** (F6): warnings, ΔBIC per component (> 10 strong, < 2 not supported), multi-start spread.
9. **Analysis → Apply model to others** (fix widths) or **Fit all**.
10. Pick a palette (top right) → **Export** → Origin `.opju` (one formatted graph per region), PNG/TIFF/SVG/PDF, a combined figure `figures/combined.png` (rows = regions, columns = samples, panels (a), (b), …), Excel.

Tips: wrong region name → right-click → **Assign element / core level…**; only 2p3/2 measured → choose `Fe 2p3/2` (singlets); **View → Language**.

## Route B: let an AI do it

1. Install the Claude desktop app (<https://claude.ai/download>), sign in, open the **Code** tab.
2. In PeakForge click **Agent** → choose your data folder → **Connect AI to this folder**. This writes `.mcp.json` (how to call PeakForge) and `AGENTS.md` (analysis rules) into the folder.
3. Open that folder in Claude's Code tab, start a session and **allow** the *peakforge* server when asked.
4. Describe the task, e.g.:

> Use PeakForge on the XPS data in this folder: create a project here, import all .spe files, charge-correct with C 1s at 284.8 eV and report the shifts, fit Ir 4f with the Ir⁰/Ir⁴⁺/Ir³⁺ preset, O 1s with the oxide preset and other regions with generic peak search, run diagnostics on every Ir 4f and list unsupported components and parameters at bounds, export Origin + PNG + Excel with the “fjord” palette, summarise the oxidation-state fractions in a table and remind me to cross-check with CasaXPS or Avantage.

Open the same `.xpsproj` in PeakForge to watch: the window reloads after every change the agent makes, and you can correct things by hand in between.

## Good habits

Keep spin–orbit splittings/ratios at literature values; use the same widths and line shapes for one chemical state across samples; report diagnostics together with fractions; **cross-check with established software before publishing** (same background type/end points, line shapes, constraints and charge reference).
