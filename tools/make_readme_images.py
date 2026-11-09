"""Rebuild docs/images from the synthetic demo data (never from real measurements).

    python tools/make_demo_data.py
    python tools/make_readme_images.py <scratch folder>      (needs Origin + originpro for origin_export.png)
"""
import glob
import os
import shutil
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from peakforge.export.figure import draw_fit, save_panel_figure, save_stack_figure  # noqa: E402
from peakforge.export.origin import export_origin  # noqa: E402
from peakforge.export.themes import grouped, theme  # noqa: E402
from peakforge.project import Project  # noqa: E402

work = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "readme"))
IMG = os.path.join(ROOT, "docs", "images")
os.makedirs(IMG, exist_ok=True)
shutil.rmtree(os.path.join(work, "demo"), ignore_errors=True)
p = Project.create(os.path.join(work, "demo"), "Demo")
for f, lab in (("demo_fresh", "Fresh"), ("demo_aged", "Aged")):
    p.add_file(os.path.join(ROOT, "examples", f + ".csv"))
    p.set_sample_label(f, lab)
p.auto_charge()
for k in p.keys(narrow_only=True):
    m, r = p.fit(k, n_starts=3)
    print(f"{k:22s} {m.preset or 'generic':18s} RMS {r.rms_pct:5.2f} %",
          {a: round(b, 1) for a, b in r.fractions.items()})

items = [(p.sample_label(p.spectra[k].sample), p.spectra[k].region, p.get_model(k), p.result(k))
         for k in p.keys("Ir 4f") + p.keys("O 1s")[:1]]
# 2x2 publication panel: Ir 4f in blues, O 1s in teal-greens, (a)-(d)
panels = []
for reg, th, style in (("Ir 4f", "glacier", "stacked"), ("O 1s", "lagoon", "inline")):
    for smp in ("demo_fresh", "demo_aged"):
        k_ = p.keys(reg, smp)[0]
        panels.append(dict(model=p.get_model(k_), result=p.result(k_), theme=th, region=reg,
                           sample=p.sample_label(smp), label_style=style))
save_panel_figure(os.path.join(IMG, "panel_example.png"), panels, ncols=2, dpi=130)
save_stack_figure(os.path.join(IMG, "compare_ir4f.png"),
                  [(s, m, r) for s, reg, m, r in items if reg == "Ir 4f"], "fjord", "Ir 4f", dpi=110)
k = p.keys("Ir 4f")[0]
m, r = p.get_model(k), p.result(k)
fig, axs = plt.subplots(6, 4, figsize=(15, 15), layout="constrained")
for i, (fid, zh, en, ids) in enumerate(grouped()[:6]):
    for j, t in enumerate(ids[:4]):
        ax = axs[i, j]
        draw_fit(ax, m, r, t, legend=False, show_labels=False, fs=7)
        th = theme(t)
        ax.set_title(f"{zh} {en} · {th['name_zh']} {th['name_en']}", loc="left", fontsize=9,
                     fontfamily=["Microsoft YaHei", "Arial"])
        ax.set_xlabel("")
fig.savefig(os.path.join(IMG, "palettes.png"), dpi=60)

try:
    out = os.path.join(work, "origin_png")
    export_origin(items, out, png=True)
    from PIL import Image
    pngs = [os.path.join(out, f"{s}_{reg.replace(' ', '')}_origin.png") for s, reg, _m, _r in items]
    ims = [Image.open(f) for f in pngs]
    ims = [i.resize((i.width * 2 // 5, i.height * 2 // 5)) for i in ims]
    c = Image.new("RGB", (sum(i.width for i in ims), max(i.height for i in ims)), "white")
    x = 0
    for i in ims:
        c.paste(i, (x, 0))
        x += i.width
    c.save(os.path.join(IMG, "origin_export.png"))
except Exception as e:      # noqa: BLE001
    print("Origin preview skipped:", e)
print("project:", p.path)
