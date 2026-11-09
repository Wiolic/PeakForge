"""Builds an Origin project from a JSON spec. Self-contained on purpose (only needs originpro +
pandas), so the very same code runs
  * from PeakForge through external-Python originpro (Origin installed), or
  * inside Origin's embedded Python:  run -pyf "<export>/build_origin.py"
when PeakForge only writes the data + script (fallback).

spec = {
  "out": "C:/.../fits.opju",
  "template": "C:/.../PeakForge_XPS.otpu" | null,        # graph template (Ir-new style)
  "graphs": [{
     "book": "S1_Ir4f", "csv": "C:/.../S1_Ir4f.csv",
     "columns": [{"name","long","units","comment","role"}],   # role: x|data|bg|env|comp|resid
     "colors": {"data":[r,g,b], "bg":[..], "env":[..], "comp":[[..],..]},
     "fill_alpha": 0.25, "line_width": 1.5, "symbol_size": 8, "font": "Arial",
     "region": "Ir 4\\i(f)", "sample": "IrTaOx-new",
     "legend": ["Measured", "Background", "Fit envelope", <components...>]  (Origin rich text),
     "xlim": [hi, lo], "png": optional path
  }]
}
"""
from __future__ import annotations

import json
import os
import sys


def _hex(c):
    r, g, b = (int(v) for v in c)
    return "#%02X%02X%02X" % (r, g, b)


def _set(lay, plot, *opts):
    """LabTalk 'set' on the dataset of a data plot (works for fill options, unlike range-based set)."""
    sname = lay.obj.GetStrProp(plot._format_property("name"))
    lay.lt_exec(";".join(f"set {sname} {o}" for o in opts) + ";")


def build(spec: dict, op=None, show: bool = False):
    import pandas as pd
    if op is None:
        import originpro as op
    if getattr(op, "oext", False):
        op.set_show(show)
    op.new()
    template = spec.get("template")
    use_tpl = bool(template) and os.path.exists(template)
    for g in spec["graphs"]:
        df = pd.read_csv(g["csv"])
        wb = op.new_book("w", lname=g["book"])
        wks = wb[0]
        wks.name = g["book"][:31]
        wks.from_df(df)
        for i, c in enumerate(g["columns"]):
            wks.set_label(i, c["long"], "L")
            wks.set_label(i, c["units"], "U")
            wks.set_label(i, c["comment"], "C")
        wks.cols_axis("X" + "Y" * (len(g["columns"]) - 1))
        roles = [c["role"] for c in g["columns"]]
        i_bg = roles.index("bg")
        gp = op.new_graph(lname=g["book"], template=template if use_tpl else "line")
        lay = gp[0]
        lw = int(g.get("line_width", 1.5) * 500)
        alpha_pct = int(round(100 * (1 - g.get("fill_alpha", 0.25))))
        legend_idx = []
        # components (bg + comp), each followed by a hidden background copy -> "fill to next plot"
        comps = [i for i, r in enumerate(roles) if r == "comp"]
        for n, ci in enumerate(comps):
            col = g["colors"]["comp"][n % len(g["colors"]["comp"])]
            p = lay.add_plot(wks, coly=ci, colx=0, type="l")
            p.color = _hex(col)
            cc = "color(%d,%d,%d)" % tuple(col)
            _set(lay, p, f"-w {lw}", "-pf 1", "-pfv 9", f"-pfb {cc}", f"-p2fb {cc}")
            p.transparency = alpha_pct
            legend_idx.append(len(lay.plot_list()))
            h = lay.add_plot(wks, coly=i_bg, colx=0, type="l")
            h.color = _hex(g["colors"]["bg"])
            _set(lay, h, "-w 0")
        pe = lay.add_plot(wks, coly=roles.index("env"), colx=0, type="l")
        pe.color = _hex(g["colors"]["env"])
        _set(lay, pe, f"-w {lw}")
        pb = lay.add_plot(wks, coly=i_bg, colx=0, type="l")
        pb.color = _hex(g["colors"]["bg"])
        _set(lay, pb, f"-w {lw}")
        pm = lay.add_plot(wks, coly=roles.index("data"), colx=0, type="s")
        pm.color = _hex(g["colors"]["data"])
        _set(lay, pm, "-k 2", "-kf 1", f"-z {g.get('symbol_size', 8)}")
        n_all = len(lay.plot_list())
        i_m, i_b, i_e = n_all, n_all - 1, n_all - 2

        # scales: reversed BE axis, headroom on top for the legend
        lo, hi = min(g["xlim"]), max(g["xlim"])
        mask = [c["role"] in ("data", "env", "bg", "comp") for c in g["columns"]]
        y = df.iloc[:, mask].to_numpy()
        ymin, ymax = float(y.min()), float(y.max())
        span = ymax - ymin
        step = 5 if hi - lo > 9 else 2
        # legend (top-left) and region/sample label (bottom-left) must stay clear of the data on the
        # high-BE (left) side: solve top and bottom limits together, as in the PNG renderer
        xcol = df.iloc[:, 0].to_numpy()
        left = xcol >= hi - 0.47 * (hi - lo)
        yl = y[left] if left.any() else y
        top_left, bot_left = float(yl.max()), float(yl.min())
        n_comp = sum(1 for c in g["columns"] if c["role"] == "comp")
        f_leg = min(0.75, 0.068 * (3 + n_comp) + 0.05)
        f_lab = 0.24
        y_lo, y_hi = ymin - 0.32 * span, ymax + 0.08 * span
        for _ in range(3):
            y_hi = max(ymax + 0.08 * span, y_lo + (top_left - y_lo) / (1 - f_leg))
            y_lo = min(ymin - 0.05 * span, bot_left - f_lab * (y_hi - y_lo))
        lay.lt_exec(f"layer.x.from={hi}; layer.x.to={lo}; layer.x.inc={step};"
                    f"layer.y.from={y_lo}; layer.y.to={y_hi};")

        entries = [f"\\l({i_m}) {g['legend'][0]}", f"\\l({i_b}) {g['legend'][1]}",
                   f"\\l({i_e}) {g['legend'][2]}"]
        entries += [f"\\l({li}) {txt}" for li, txt in zip(legend_idx, g["legend"][3:])]
        leg = "%(CRLF)".join(entries)
        region = g.get("region", "").replace('"', "'")
        sample = g.get("sample", "").replace('"', "'")
        if use_tpl:
            font = g.get("font", "Arial")
            lay.lt_exec(f'legend.text$="{leg}"; Text.text$="{region}"; Text2.text$="{sample}";'
                        f"legend.font=font({font}); Text.font=font({font}); Text2.font=font({font});"
                        f"xb.font=font({font}); yl.font=font({font}); layer.x.label.font=font({font});")
        else:
            font = g.get("font", "Arial")
            x_left = hi - 0.03 * (hi - lo)
            lay.lt_exec(
                'xb.text$="Binding energy (eV)"; yl.text$="Intensity (a.u.)";'
                "layer.y.showLabels=0; layer.y.ticks=0; layer.y.minorTicks=0;"
                f'legend -r; legend.text$="{leg}"; legend.font=font({font}); legend.showframe=0;'
                f"legend.x1={x_left}; legend.y2={ymax + 0.52 * span};"
                f'label -s -sa -n Text "{region}%(CRLF){sample}"; Text.font=font({font});'
                f"Text.showframe=0; Text.x1={x_left}; Text.y1={ymin - 0.25 * span};")
        if g.get("png"):
            gp.save_fig(g["png"], width=1600)
    op.save(spec["out"])
    return spec["out"]


if __name__ == "__main__":
    # inside Origin:  run -pyf "path/build_origin.py"   (spec.json in the same folder)
    here = os.path.dirname(os.path.abspath(__file__ if "__file__" in globals() else sys.argv[0]))
    with open(os.path.join(here, "spec.json"), encoding="utf-8") as f:
        build(json.load(f))
