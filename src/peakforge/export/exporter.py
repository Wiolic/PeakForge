"""One entry point for all exports of a project: PNG/TIFF/SVG figures, Excel workbook, Origin."""
from __future__ import annotations

import os
import re

import pandas as pd

from ..core import quant
from .curves import component_table, curve_table
from .figure import save_fit_figure, save_panel_figure, save_stack_figure
from .origin import export_origin
from .themes import comp_color, to_hex
from ..logs import log


def _safe(s: str) -> str:
    return re.sub(r"[^\w\-]+", "_", s).strip("_")[:60]


def fitted_items(project, keys=None):
    out = []
    for k in keys or project.keys(narrow_only=True):
        try:
            m = project.get_model(k)
        except ValueError as e:         # SchemaError: invalid model file → skip this spectrum
            log.warning("export: skipping %s: %s", k, e)
            continue
        if m is None:
            continue
        r = project.result(k)
        if r is None:
            continue
        s = project.spectra[k]
        out.append((k, project.sample_label(s.sample), s.region, m, r))
    return out


def snapshot(project, keys=None, with_quant: bool = True, theme: str | None = None) -> dict:
    """Everything an export needs, read from the project in the calling (UI) thread: fitted items, charge
    shifts, quantification, project name and settings. run_export then works on this copy only, so it can run
    in a worker thread (see peakforge.tasks).
    Colours: every figure gets its theme dict from the project palette (per-figure settings included);
    `theme` (a combo id) overrides the whole palette for this export."""
    items = fitted_items(project, keys)
    pal = project.palette() if theme is None else dict(combo=theme)
    themes = {k: project.figure_theme(k, len(m.components), palette=pal) for k, _s, _g, m, _r in items}
    n_by_region: dict = {}
    for _k, _s, reg, m, _r in items:
        n_by_region[reg] = max(n_by_region.get(reg, 0), len(m.components))
    region_themes = {reg: project.figure_theme(None, n, region=reg, palette=pal) for reg, n in n_by_region.items()}
    return dict(items=items, themes=themes, region_themes=region_themes,
                shifts={k: project.shift(project.spectra[k].sample) for k, *_ in items},
                quant=project.quantify(results={k: r for k, _s, _g, _m, r in items}) if with_quant else [],
                sample_labels={e_s: project.sample_label(e_s) for e_s in project.samples()},
                name=project.name, charge_ref=project.settings.get("charge_ref", 284.8),
                theme=pal.get("combo", "glacier"))


def _write_excel(snap: dict, path: str) -> str:
    items = snap["items"]
    with pd.ExcelWriter(path) as w:
        comp = pd.concat([component_table(m, r, smp, reg) for _k, smp, reg, m, r in items],
                         ignore_index=True) if items else pd.DataFrame()
        comp.round(4).to_excel(w, sheet_name="Components", index=False)
        qual = pd.DataFrame([{"Sample": smp, "Region": reg, "Residual RMS (% peak)": r.rms_pct,
                              "Reduced chi2": r.chi2_red, "BIC": r.bic, "Free params": r.n_free,
                              "Params at bounds": ", ".join(r.bound_hits),
                              "Charge shift (eV)": snap["shifts"][k],
                              "Background": m.background.kind}
                             for k, smp, reg, m, r in items])
        qual.round(4).to_excel(w, sheet_name="Fit quality", index=False)
        q = snap["quant"]
        if q:
            qd = pd.DataFrame([{"Sample": snap["sample_labels"].get(e["sample"], e["sample"]), "Region": e["region"],
                                "Area": e["area"], "Area source": e["area_source"], "RSF": e.get("rsf"),
                                "Atomic %": e.get("at_pct")} for e in q])
            qd = pd.concat([qd.round(4), pd.DataFrame([{"Sample": "Method", "Region": quant.QUANT_METHOD}])],
                           ignore_index=True)
            qd.to_excel(w, sheet_name="Quantification", index=False)
        rows = []
        for k, smp, reg, m, _r in items:
            th = snap["themes"][k]
            rows += [dict(Sample=smp, Region=reg, Element=c.label or c.name,
                          Colour=to_hex(comp_color(th, i, c.color))) for i, c in enumerate(m.components)]
            rows += [dict(Sample=smp, Region=reg, Element=lab, Colour=to_hex(th[key]))
                     for lab, key in (("Measured", "data"), ("Background", "background"), ("Fit envelope", "envelope"))]
        pd.DataFrame(rows).rename(columns={"Element": "Item"}).to_excel(w, sheet_name="Colours", index=False)
        from .. import CREDIT, DISCLAIMER_EN, DISCLAIMER_ZH, __version__
        pd.DataFrame({"Item": ["Software", "Credit", "Project", "Charge reference (eV)", "Disclaimer", "免责声明"],
                      "Value": [f"PeakForge {__version__}", CREDIT, snap["name"],
                                snap["charge_ref"], DISCLAIMER_EN, DISCLAIMER_ZH]}
                     ).to_excel(w, sheet_name="About", index=False)
        used = set()
        for k, smp, reg, m, r in items:
            df, _ = curve_table(m, r)
            name = _safe(f"{smp}_{reg}")[:31]
            while name in used:
                name = name[:28] + str(len(used))
            used.add(name)
            df.to_excel(w, sheet_name=name, index=False)
    return path


def export_excel(project, path: str, keys=None) -> str:
    return _write_excel(snapshot(project, keys), path)


def collect_export(project, keys=None, out_dir: str | None = None, theme: str | None = None,
                   formats=("png", "xlsx", "origin"), dpi: int = 300, stack: bool = True) -> dict:
    """UI-thread half of an export: read the project into a job for run_export."""
    out_dir = out_dir or project.out_dir("export")
    os.makedirs(out_dir, exist_ok=True)
    snap = snapshot(project, keys, with_quant="xlsx" in formats, theme=theme)
    return dict(snap=snap, out_dir=out_dir, theme=snap["theme"], formats=tuple(formats), dpi=dpi, stack=stack)


def run_export(job: dict, progress=None) -> dict:
    """Worker-thread half: figures, Excel, Origin from the snapshot only (never touches the Project).
    progress(f, text): optional hook, also the cancellation point (peakforge.tasks)."""
    snap, out_dir, formats, dpi, stack = (job[k] for k in ("snap", "out_dir", "formats", "dpi", "stack"))
    items = snap["items"]
    res: dict = dict(out_dir=out_dir, figures=[], n=len(items))
    figs = [f for f in formats if f in ("png", "tiff", "svg", "pdf")]
    total = len(items) * len(figs) + 3
    done = 0

    def step(text):
        nonlocal done
        if progress is not None:
            progress(done / total, text)
        done += 1
    for k, smp, reg, m, r in items:
        for ext in figs:
            step(f"{smp} {reg}")
            p = os.path.join(out_dir, "figures", _safe(f"{smp}_{reg}") + "." + ext)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            save_fit_figure(p, m, r, snap["themes"][k], smp, reg, dpi=dpi)
            res["figures"].append(p)
    if stack and figs:
        step("compare")
        by_region: dict = {}
        for k, smp, reg, m, r in items:
            by_region.setdefault(reg, []).append((smp, m, r))
        for reg, its in by_region.items():
            if len(its) > 1:
                p = os.path.join(out_dir, "figures", "compare_" + _safe(reg) + "." + figs[0])
                save_stack_figure(p, its, snap["region_themes"][reg], reg, dpi=dpi)
                res["figures"].append(p)
    if figs and len(items) > 1:
        # combined publication figure: rows = regions, columns = samples, panels (a), (b), …
        regions = list(dict.fromkeys(reg for _k, _s, reg, _m, _r in items))
        samples = list(dict.fromkeys(smp for _k, smp, _reg, _m, _r in items))
        grid = {(reg, smp): (m, r) for _k, smp, reg, m, r in items}
        ths = {(reg, smp): snap["themes"][k] for k, smp, reg, _m, _r in items}
        panels = [dict(model=grid[(reg, smp)][0], result=grid[(reg, smp)][1], theme=ths[(reg, smp)], region=reg,
                       sample=smp) for reg in regions for smp in samples if (reg, smp) in grid]
        p = os.path.join(out_dir, "figures", "combined." + figs[0])
        save_panel_figure(p, panels, ncols=min(len(samples), 3), dpi=dpi)
        res["figures"].append(p)
    if "xlsx" in formats:
        step("Excel")
        res["xlsx"] = _write_excel(snap, os.path.join(out_dir, _safe(snap["name"]) + "_results.xlsx"))
    if "origin" in formats and items:
        step("Origin")
        res["origin"] = export_origin([(smp, reg, m, r) for _k, smp, reg, m, r in items],
                                      os.path.join(out_dir, "origin"), _safe(snap["name"]) + ".opju",
                                      [snap["themes"][k] for k, *_ in items])
    if progress is not None:
        progress(1.0, "")
    return res


def export_all(project, keys=None, out_dir: str | None = None, theme: str | None = None,
               formats=("png", "xlsx", "origin"), dpi: int = 300, stack: bool = True) -> dict:
    return run_export(collect_export(project, keys, out_dir, theme, formats, dpi, stack))


FIGURE_EXTS = (".png", ".svg", ".pdf", ".tif", ".tiff")


def collect_export_one(project, key: str, path: str, theme: str | None = None, dpi: int = 300,
                       size: tuple[float, float] = (5.0, 4.0), transparent: bool = False,
                       residual: bool = False) -> dict:
    """UI-thread half of a single-figure export. The format follows the extension of `path`:
    .png/.svg/.pdf/.tif(f) = figure, .opju = one-graph Origin project (data + origin_builder.py next to it
    when originpro is not available)."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in FIGURE_EXTS + (".opju",):
        raise ValueError(f"Unsupported export format '{ext}' (use {', '.join(FIGURE_EXTS + ('.opju',))})")
    snap = snapshot(project, [key], with_quant=False, theme=theme)
    if not snap["items"]:
        raise ValueError(f"{key}: no fitted model to export (fit it first)")
    d = os.path.dirname(os.path.abspath(path))
    os.makedirs(d, exist_ok=True)
    return dict(snap=snap, path=os.path.abspath(path), ext=ext, dpi=dpi,
                size=tuple(size), transparent=transparent, residual=residual)


def run_export_one(job: dict, progress=None) -> dict:
    """Worker-thread half: render the single figure from the snapshot only."""
    k, smp, reg, m, r = job["snap"]["items"][0]
    th = job["snap"]["themes"][k]
    path = job["path"]
    if progress is not None:
        progress(0.0, f"{smp} {reg}")
    if job["ext"] == ".opju":
        # data + builder script go to '<stem>_origin/'; the .opju itself is written at `path` (absolute
        # opju name: make_spec joins it unchanged), so the reported path is where the file is
        out = export_origin([(smp, reg, m, r)], os.path.join(os.path.dirname(path), _safe(os.path.splitext(
            os.path.basename(path))[0]) + "_origin"), path, th)
        res = dict(path=path if out.get("opju") else out["script"], origin=out)
    else:
        save_fit_figure(path, m, r, th, smp, reg, dpi=job["dpi"], size=job["size"],
                        residual=job["residual"], transparent=job["transparent"])
        res = dict(path=path)
    if progress is not None:
        progress(1.0, "")
    return res


def export_one(project, key: str, path: str, theme: str | None = None, dpi: int = 300,
               size: tuple[float, float] = (5.0, 4.0), transparent: bool = False, residual: bool = False) -> dict:
    return run_export_one(collect_export_one(project, key, path, theme, dpi, size, transparent, residual))
