"""Origin export: data (CSV) + spec; then build the .opju through originpro if available,
otherwise leave a script that Origin runs itself (run -pyf build_origin.py)."""
from __future__ import annotations

import json
import os
import re
import shutil

from ..core.fit import FitResult
from ..core.model import RegionModel
from .curves import curve_table
from .themes import comp_color, label_origin, region_origin, theme


def originpro_available() -> bool:
    try:
        import originpro  # noqa: F401
        return True
    except Exception:       # noqa: BLE001
        return False


def _safe(s: str) -> str:
    return re.sub(r"[^\w\-]+", "_", s).strip("_")[:40]


def make_spec(items: list[tuple[str, str, RegionModel, FitResult]], out_dir: str, opju_name: str,
              th_name: str | None = None, png: bool = False) -> dict:
    """items: [(sample_label, region, model, result)]"""
    os.makedirs(out_dir, exist_ok=True)
    th = theme(th_name)
    graphs = []
    for sample, region, model, res in items:
        df, meta = curve_table(model, res)
        book = _safe(f"{sample}_{region.replace(' ', '')}")
        csv = os.path.join(out_dir, book + ".csv")
        df.to_csv(csv, index=False, encoding="utf-8")
        roles = ["x", "data", "bg", "env"] + ["comp"] * (len(meta) - 5) + ["resid"]
        cols = [dict(m, role=r) for m, r in zip(meta, roles)]
        comp_cols = [comp_color(th, i, c.color) for i, c in enumerate(model.components)]
        graphs.append(dict(
            book=book, csv=os.path.abspath(csv), columns=cols,
            colors=dict(data=th["data"], bg=th["background"], env=th["envelope"], comp=comp_cols),
            fill_alpha=th["fill_alpha"], line_width=th["line_width"], symbol_size=th["data_size"],
            font=th["font"],
            region=region_origin(region), sample=label_origin(sample),
            legend=["Measured", "Background", "Fit envelope"] + [label_origin(c.label or c.name)
                                                                for c in model.components],
            legend_order=[model.names().index(c.name) for c in model.legend_components()],
            xlim=[float(res.x.max()), float(res.x.min())],
            png=os.path.abspath(os.path.join(out_dir, book + "_origin.png")) if png else None))
    tpl = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "PeakForge_XPS.otpu")
    tpl_out = None
    if os.path.exists(tpl):
        tpl_out = os.path.abspath(os.path.join(out_dir, "PeakForge_XPS.otpu"))
        shutil.copy(tpl, tpl_out)
    return dict(out=os.path.abspath(os.path.join(out_dir, opju_name)), template=tpl_out, graphs=graphs)


def write_script(spec: dict, out_dir: str) -> str:
    """Fallback: spec.json + build_origin.py; in Origin: run -pyf "<out_dir>/build_origin.py"."""
    with open(os.path.join(out_dir, "spec.json"), "w", encoding="utf-8") as f:
        json.dump(spec, f, ensure_ascii=False, indent=1)
    dst = os.path.join(out_dir, "build_origin.py")
    shutil.copy(os.path.join(os.path.dirname(__file__), "origin_builder.py"), dst)
    with open(os.path.join(out_dir, "README_Origin.txt"), "w", encoding="utf-8") as f:
        f.write("Open Origin, then in the Script Window (Window > Script Window) run:\n"
                f'    run -pyf "{os.path.abspath(dst)}"\n'
                "The project is saved to: " + spec["out"] + "\n")
    return dst


def export_origin(items, out_dir: str, opju_name: str = "PeakForge_fits.opju", th_name=None,
                  use_originpro: bool | None = None, png: bool = False) -> dict:
    spec = make_spec(items, out_dir, opju_name, th_name, png)
    script = write_script(spec, out_dir)
    if use_originpro is None:
        use_originpro = originpro_available()
    if use_originpro:
        import originpro as op
        from . import origin_builder
        try:
            origin_builder.build(spec, op)
        finally:
            try:
                op.exit()
            except Exception:   # noqa: BLE001
                pass
        return dict(mode="originpro", opju=spec["out"], script=script)
    return dict(mode="script", opju=None, script=script,
                hint=f'In Origin: run -pyf "{os.path.abspath(script)}"')
