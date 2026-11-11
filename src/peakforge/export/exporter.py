"""One entry point for all exports of a project: PNG/TIFF/SVG figures, Excel workbook, Origin."""
from __future__ import annotations

import os
import re

import pandas as pd

from ..core import quant
from .curves import component_table, curve_table
from .figure import save_fit_figure, save_panel_figure, save_stack_figure
from .origin import export_origin
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


def snapshot(project, keys=None, with_quant: bool = True) -> dict:
    """Everything an export needs, read from the project in the calling (UI) thread: fitted items, charge
    shifts, quantification, project name and settings. run_export then works on this copy only, so it can run
    in a worker thread (see peakforge.tasks)."""
    items = fitted_items(project, keys)
    return dict(items=items,
                shifts={k: project.shift(project.spectra[k].sample) for k, *_ in items},
                quant=project.quantify(results={k: r for k, _s, _g, _m, r in items}) if with_quant else [],
                sample_labels={e_s: project.sample_label(e_s) for e_s in project.samples()},
                name=project.name, charge_ref=project.settings.get("charge_ref", 284.8),
                theme=project.settings.get("theme", "glacier"))


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
    snap = snapshot(project, keys, with_quant="xlsx" in formats)
    return dict(snap=snap, out_dir=out_dir, theme=theme or snap["theme"], formats=tuple(formats), dpi=dpi, stack=stack)


def run_export(job: dict, progress=None) -> dict:
    """Worker-thread half: figures, Excel, Origin from the snapshot only (never touches the Project).
    progress(f, text): optional hook, also the cancellation point (peakforge.tasks)."""
    snap, out_dir, theme, formats, dpi, stack = (job[k] for k in ("snap", "out_dir", "theme", "formats", "dpi", "stack"))
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
            save_fit_figure(p, m, r, theme, smp, reg, dpi=dpi)
            res["figures"].append(p)
    if stack and figs:
        step("compare")
        by_region: dict = {}
        for k, smp, reg, m, r in items:
            by_region.setdefault(reg, []).append((smp, m, r))
        for reg, its in by_region.items():
            if len(its) > 1:
                p = os.path.join(out_dir, "figures", "compare_" + _safe(reg) + "." + figs[0])
                save_stack_figure(p, its, theme, reg, dpi=dpi)
                res["figures"].append(p)
    if figs and len(items) > 1:
        # combined publication figure: rows = regions, columns = samples, panels (a), (b), …
        regions = list(dict.fromkeys(reg for _k, _s, reg, _m, _r in items))
        samples = list(dict.fromkeys(smp for _k, smp, _reg, _m, _r in items))
        grid = {(reg, smp): (m, r) for _k, smp, reg, m, r in items}
        panels = [dict(model=grid[(reg, smp)][0], result=grid[(reg, smp)][1], theme=theme, region=reg,
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
                                      os.path.join(out_dir, "origin"), _safe(snap["name"]) + ".opju", theme)
    if progress is not None:
        progress(1.0, "")
    return res


def export_all(project, keys=None, out_dir: str | None = None, theme: str | None = None,
               formats=("png", "xlsx", "origin"), dpi: int = 300, stack: bool = True) -> dict:
    return run_export(collect_export(project, keys, out_dir, theme, formats, dpi, stack))
