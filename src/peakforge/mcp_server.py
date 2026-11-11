"""MCP server: lets an AI agent (Claude Code, Codex, Cursor …) drive PeakForge.

Run:  peakforge mcp      (stdio transport)
Every tool takes an optional `project` (path to a .xpsproj or its folder). If omitted, the last
project opened in this server session — or $PEAKFORGE_PROJECT — is used. The desktop app watches
the project folder, so changes made here appear in an open GUI window.
"""
from __future__ import annotations

import os

from mcp.server import MCPServer

from . import __version__, ops
from .project import Project, _jsonable

INSTRUCTIONS = """PeakForge XPS analysis. Typical workflow:
1. create_project / open_project, then add_files (.vms/.spe/.csv/.xlsx; raw files are copied read-only).
2. charge_correct (C 1s C–C → 284.8 eV by default) — check the shift per sample in status.
3. For each region: list_presets(region) → apply_preset(key, preset_id), or add_component manually.
4. fit(keys) → read rms_pct, bound_hits; diagnostics(key) for ΔBIC component significance,
   parameter correlations and multi-start stability BEFORE reporting oxidation-state fractions.
5. Adjust with set_param (value/min/max/vary/expr links like "Ir4.fwhm"), set_background, refit.
6. batch_apply to reuse one model across samples; quantify; export (png/xlsx/origin).
Rules: never edit files in data/raw. Report fitted numbers with their diagnostics; say when a
component is 'not supported' by ΔBIC.
Always remind the user that results should be cross-checked against established XPS
software (CasaXPS, Avantage, MultiPak) before publication. Spectrum keys look like 'sample/region', e.g. 'S1/Ir 4f'."""

mcp = MCPServer("PeakForge", instructions=INSTRUCTIONS, version=__version__)
_state: dict = {"path": os.environ.get("PEAKFORGE_PROJECT")}


def _p(project: str | None) -> Project:
    path = project or _state.get("path")
    if not path:
        raise ValueError("No project: call open_project or create_project first, or pass project=")
    p = Project.open(path)
    _state["path"] = p.path
    return p


@mcp.tool()
def create_project(folder: str, name: str | None = None) -> dict:
    """Create a new PeakForge project folder (with <name>.xpsproj) and make it current."""
    p = Project.create(folder, name)
    _state["path"] = p.path
    return dict(project=p.path)


@mcp.tool()
def open_project(project: str) -> dict:
    """Open an existing project (.xpsproj file or its folder) and return its status."""
    return ops.status(_p(project))


@mcp.tool()
def status(project: str | None = None) -> dict:
    """Samples (charge shifts), spectra keys, regions, which spectra have models / fit RMS."""
    return ops.status(_p(project))


@mcp.tool()
def add_files(files: list[str], project: str | None = None, sample: str | None = None) -> dict:
    """Import data files (.vms VAMAS, .spe PHI, .csv/.txt/.xlsx). Returns the new spectrum keys."""
    p = _p(project)
    return {f: p.add_file(f, sample=sample if len(files) == 1 else None) for f in files}


@mcp.tool()
def charge_correct(project: str | None = None, sample: str | None = None, ref: float | None = None,
                   shift: float | None = None) -> dict:
    """Charge correction. With `shift` (eV, added to BE) set it manually for `sample`; otherwise
    auto-reference the C 1s C–C peak to `ref` (default project setting, 284.8 eV)."""
    p = _p(project)
    if shift is not None:
        if not sample:
            raise ValueError("sample is required with shift")
        p.set_shift(sample, shift)
        return {sample: shift}
    out = p.auto_charge(sample, ref)
    return dict(shifts=out, failed=p.charge_failures) if p.charge_failures else out


@mcp.tool()
def spectrum_data(key: str, project: str | None = None, max_points: int = 400) -> dict:
    """Raw data of a spectrum (BE after charge shift, cps), decimated to max_points."""
    p = _p(project)
    k = ops.resolve_key(p, key)
    s = p.spectra[k]
    step = max(1, len(s.be) // max_points)
    sh = p.shift(s.sample)
    return dict(key=k, shift=sh, be=[round(float(v) + sh, 3) for v in s.be[::step]],
                cps=[round(float(v), 2) for v in s.cps[::step]], meta=_jsonable(s.meta))


@mcp.tool()
def list_presets(region: str | None = None, project: str | None = None) -> list[dict]:
    """Built-in, user and project peak-model presets (optionally for one region, e.g. 'Ir 4f')."""
    p = _p(project) if (project or _state.get("path")) else None
    return ops.list_presets(p, region)


@mcp.tool()
def apply_preset(key: str, preset_id: str | None = None, project: str | None = None) -> dict:
    """Start the model of spectrum `key` from a preset. preset_id='__generic__' = automatic peak finding
    for ANY element (doublets with tabulated splitting); None = first preset for the region, else generic.
    Background end points and initial areas are set from the data."""
    return ops.apply_preset(_p(project), key, preset_id)


@mcp.tool()
def list_orbitals(element: str | None = None) -> list[dict]:
    """Core-level table (Li–U): typical BE, spin–orbit split, area ratio, multiplet flag. Filter by element."""
    return ops.list_orbitals(element)


@mcp.tool()
def set_region(key: str, region: str, project: str | None = None) -> dict:
    """Assign the element / core level of a spectrum, e.g. a CSV column -> 'Fe 2p' or 'Ce 3d'.
    Region labels: '<El> <n><l>' (doublet) or '<El> <n><l><j>' like 'Fe 2p3/2' (single sub-level)."""
    return ops.set_region(_p(project), key, region)


@mcp.tool()
def get_model(key: str, project: str | None = None) -> dict:
    """Full model JSON (components, parameters with bounds/links, background) + last fit summary."""
    return ops.model_json(_p(project), key)


@mcp.tool()
def set_model(key: str, model: dict, project: str | None = None) -> dict:
    """Replace the whole model (same JSON structure as get_model()['model'])."""
    return ops.set_model(_p(project), key, model)


@mcp.tool()
def add_component(key: str, center: float, label: str = "", fwhm: float = 1.2, shape: str = "gl",
                  doublet: bool | None = None, split: float | None = None, ratio: float | None = None,
                  center_window: float = 1.0, in_total: bool = True, project: str | None = None) -> dict:
    """Add a peak. shape: gaussian|lorentzian|pvoigt|gl|sgl|voigt|ds|la. doublet defaults to the
    orbital's spin-orbit data (split, area ratio). in_total=False excludes it (e.g. satellite) from fractions."""
    return ops.add_component(_p(project), key, None, center, fwhm, shape, label, doublet, split, ratio,
                             center_window, in_total)


@mcp.tool()
def remove_component(key: str, name: str, project: str | None = None) -> dict:
    """Remove a component by name."""
    return ops.remove_component(_p(project), key, name)


@mcp.tool()
def set_param(key: str, param: str, value: float | None = None, min: float | None = None,
              max: float | None = None, vary: bool | None = None, expr: str | None = None,
              project: str | None = None) -> dict:
    """Set a parameter 'Comp.param' (center, fwhm, area, eta, m, alpha, gamma, split, ratio …).
    expr links it to others, e.g. 'Ir4.fwhm' or 'Ir0.center + 1.0'; expr='' removes the link."""
    return ops.set_param(_p(project), key, param, value, min, max, vary, expr)


@mcp.tool()
def set_background(key: str, kind: str | None = None, lo: float | None = None, hi: float | None = None,
                   fit_lo: float | None = None, fit_hi: float | None = None, project: str | None = None) -> dict:
    """Background kind (shirley|linear|tougaard|smart|none), its BE end points lo/hi, fit window."""
    return ops.set_background(_p(project), key, kind, lo, hi, fit_lo, fit_hi)


@mcp.tool()
def fit(keys: list[str] | None = None, region: str | None = None, sample: str | None = None,
        n_starts: int = 3, deep_diagnostics: bool = False, project: str | None = None) -> list[dict]:
    """Fit spectra (given keys, or all narrow scans of a region/sample). Missing models are created
    from presets. Returns RMS residual (% of peak height), fractions, components, bound hits."""
    return ops.fit(_p(project), keys, region, sample, n_starts, deep_diagnostics)


@mcp.tool()
def diagnostics(key: str, project: str | None = None) -> dict:
    """Fit quality: bounds, |corr|>0.95, ΔBIC on removing each component, multi-start fraction spread,
    and plain-language warnings."""
    return ops.diagnostics(_p(project), key, True)


@mcp.tool()
def batch_apply(source_key: str, targets: list[str] | None = None, fix: list[str] | None = None,
                n_starts: int = 3, project: str | None = None) -> list[dict]:
    """Copy the model of source_key to other spectra of the same region and fit them. `fix` freezes
    parameters at the source values (e.g. ['fwhm','eta','alpha','gamma'])."""
    return ops.batch(_p(project), source_key, None, targets, tuple(fix or ["fwhm"]), n_starts)


@mcp.tool()
def quantify(project: str | None = None) -> list[dict]:
    """Atomic % per sample from fitted (or raw background-subtracted) areas / RSF."""
    return _jsonable(_p(project).quantify())


@mcp.tool()
def export(formats: list[str] | None = None, theme: str | None = None, keys: list[str] | None = None,
           project: str | None = None) -> dict:
    """Export figures (png/tiff/svg/pdf), Excel (xlsx) and Origin (.opju via Origin, else a script)
    to <project>/output/export. Themes (landscape names, 6 families x 4): glacier (default), fjord, lagoon, abyss, moss, pinewood, bamboo, rainforest, desert, canyon, loess, badlands, dawn, dusk, aurora, twilight, basalt, granite, slate, highland, lavender, meadow, autumn, prairie; custom ones are "user:<id>"."""
    from .export.exporter import export_all
    p = _p(project)
    return _jsonable(export_all(p, keys and [ops.resolve_key(p, k) for k in keys], theme=theme,
                                formats=tuple(formats or ("png", "xlsx", "origin"))))


@mcp.tool()
def render(key: str, project: str | None = None, theme: str | None = None) -> dict:
    """Render the current fit of one spectrum to a PNG and return its path (to look at the fit)."""
    from .export.figure import save_fit_figure
    p = _p(project)
    k = ops.resolve_key(p, key)
    m = p.get_model(k)
    if m is None:
        raise ValueError("no model")
    s = p.spectra[k]
    path = os.path.join(p.out_dir("agent"), k.replace("/", "_").replace(" ", "") + ".png")
    save_fit_figure(path, m, p.result(k), theme, p.sample_label(s.sample), s.region, dpi=150, residual=True)
    return dict(png=path)


def main():
    mcp.run("stdio")
    return 0


if __name__ == "__main__":
    main()
