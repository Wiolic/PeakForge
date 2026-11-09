"""One entry point for all exports of a project: PNG/TIFF/SVG figures, Excel workbook, Origin."""
from __future__ import annotations

import os
import re

import pandas as pd

from .curves import component_table, curve_table
from .figure import save_fit_figure, save_panel_figure, save_stack_figure
from .origin import export_origin


def _safe(s: str) -> str:
    return re.sub(r"[^\w\-]+", "_", s).strip("_")[:60]


def fitted_items(project, keys=None):
    out = []
    for k in keys or project.keys(narrow_only=True):
        m = project.get_model(k)
        if m is None:
            continue
        r = project.result(k)
        if r is None:
            continue
        s = project.spectra[k]
        out.append((k, project.sample_label(s.sample), s.region, m, r))
    return out


def export_excel(project, path: str, keys=None) -> str:
    items = fitted_items(project, keys)
    with pd.ExcelWriter(path) as w:
        comp = pd.concat([component_table(m, r, smp, reg) for _k, smp, reg, m, r in items],
                         ignore_index=True) if items else pd.DataFrame()
        comp.round(4).to_excel(w, sheet_name="Components", index=False)
        qual = pd.DataFrame([{"Sample": smp, "Region": reg, "Residual RMS (% peak)": r.rms_pct,
                              "Reduced chi2": r.chi2_red, "BIC": r.bic, "Free params": r.n_free,
                              "Params at bounds": ", ".join(r.bound_hits),
                              "Charge shift (eV)": project.shift(project.spectra[k].sample),
                              "Background": m.background.kind}
                             for k, smp, reg, m, r in items])
        qual.round(4).to_excel(w, sheet_name="Fit quality", index=False)
        q = project.quantify()
        if q:
            qd = pd.DataFrame([{"Sample": project.sample_label(e["sample"]), "Region": e["region"],
                                "Area": e["area"], "Area source": e["area_source"], "RSF": e.get("rsf"),
                                "Atomic %": e.get("at_pct")} for e in q])
            qd.round(4).to_excel(w, sheet_name="Quantification", index=False)
        from .. import CREDIT, DISCLAIMER_EN, DISCLAIMER_ZH, __version__
        pd.DataFrame({"Item": ["Software", "Credit", "Project", "Charge reference (eV)", "Disclaimer", "免责声明"],
                      "Value": [f"PeakForge {__version__}", CREDIT, project.name,
                                project.settings.get("charge_ref", 284.8), DISCLAIMER_EN, DISCLAIMER_ZH]}
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


def export_all(project, keys=None, out_dir: str | None = None, theme: str | None = None,
               formats=("png", "xlsx", "origin"), dpi: int = 300, stack: bool = True) -> dict:
    out_dir = out_dir or project.out_dir("export")
    os.makedirs(out_dir, exist_ok=True)
    theme = theme or project.settings.get("theme", "glacier")
    items = fitted_items(project, keys)
    res: dict = dict(out_dir=out_dir, figures=[], n=len(items))
    figs = [f for f in formats if f in ("png", "tiff", "svg", "pdf")]
    for k, smp, reg, m, r in items:
        for ext in figs:
            p = os.path.join(out_dir, "figures", _safe(f"{smp}_{reg}") + "." + ext)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            save_fit_figure(p, m, r, theme, smp, reg, dpi=dpi)
            res["figures"].append(p)
    if stack and figs:
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
        res["xlsx"] = export_excel(project, os.path.join(out_dir, _safe(project.name) + "_results.xlsx"), keys)
    if "origin" in formats and items:
        res["origin"] = export_origin([(smp, reg, m, r) for _k, smp, reg, m, r in items],
                                      os.path.join(out_dir, "origin"), _safe(project.name) + ".opju", theme)
    return res
