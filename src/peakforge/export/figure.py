"""Matplotlib rendering in the project theme (PNG / TIFF / SVG / PDF) and for the GUI canvas."""
from __future__ import annotations

import logging

import matplotlib
import numpy as np

from ..core.fit import FitResult
from ..core.model import RegionModel
from .themes import comp_color, label_mathtext, region_mathtext, rgb01, theme

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


def style_axes(ax, th: dict, fs: float = 12):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(1.2)
    ax.set_yticks([])
    ax.tick_params(axis="x", direction="out", width=1.2, length=5, labelsize=fs)
    ax.tick_params(axis="x", which="minor", direction="out", width=1.0, length=3)
    from matplotlib.ticker import AutoMinorLocator
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.set_xlabel("Binding energy (eV)", fontsize=fs + 2, fontfamily=th["font"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=fs + 2, fontfamily=th["font"])
    for lab in ax.get_xticklabels():
        lab.set_fontfamily(th["font"])


def draw_fit(ax, model: RegionModel, res: FitResult, th_name: str | None = None, sample: str = "",
             region: str = "", legend: bool = True, residual_ax=None, fs: float = 12,
             offset: float = 0.0, show_labels: bool = True, legend_kw: dict | None = None):
    th = theme(th_name)
    x = res.x
    o = np.argsort(x)
    x = x[o]
    bg = res.bg[o] + offset
    for i, c in enumerate(model.components):
        col = rgb01(comp_color(th, i, c.color))
        tot = np.sum(res.comp_curves[c.name], axis=0)[o]
        ax.fill_between(x, bg, bg + tot, color=col, alpha=th["fill_alpha"], lw=0, label=label_mathtext(c.label or c.name))
        ax.plot(x, bg + tot, color=col, lw=th["line_width"] * 0.8)
    ax.plot(x, bg, color=rgb01(th["background"]), lw=th["line_width"], label="Background")
    ax.plot(x, res.envelope[o] + offset, color=rgb01(th["envelope"]), lw=th["line_width"], label="Fit envelope")
    ax.plot(x, res.y[o] + offset, "o", ms=th["data_size"] * 0.55, mfc="none", mec=rgb01(th["data"]),
            mew=1.0, label="Measured", zorder=5)
    ax.set_xlim(x.max(), x.min())
    if show_labels and offset == 0.0:
        ymin = float(min(res.y.min(), res.bg.min()))
        ymax = float(max(res.y.max(), res.envelope.max()))
        span = ymax - ymin or 1.0
        ax.set_ylim(ymin - 0.3 * span, ymax + 0.55 * span)
    style_axes(ax, th, fs)
    if legend:
        h, lab = ax.get_legend_handles_labels()
        order = [lab.index("Measured"), lab.index("Background"), lab.index("Fit envelope")] + \
                [i for i, l_ in enumerate(lab) if l_ not in ("Measured", "Background", "Fit envelope")]
        kw = dict(frameon=False, loc="upper left", prop={"family": th["font"], "size": fs})
        kw.update(legend_kw or {})
        ax.legend([h[i] for i in order], [lab[i] for i in order], **kw)
    if show_labels:
        txt = region_mathtext(region or model.region)
        if sample:
            txt += "\n" + sample
        ax.text(0.03, 0.04, txt, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=fs + 1, fontfamily=th["font"])
    if residual_ax is not None:
        residual_ax.axhline(0, color="0.6", lw=0.8)
        residual_ax.plot(x, res.residual[o], color=rgb01(th["envelope"]), lw=0.8)
        residual_ax.set_xlim(x.max(), x.min())
        residual_ax.set_yticks([])
        for s in ("top", "right"):
            residual_ax.spines[s].set_visible(False)
        residual_ax.tick_params(labelbottom=False)


def save_fit_figure(path: str, model: RegionModel, res: FitResult, th_name: str | None = None,
                    sample: str = "", region: str = "", dpi: int = 300, size=(5.0, 4.0),
                    residual: bool = False):
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    if residual:
        fig, (axr, ax) = plt.subplots(2, 1, figsize=(size[0], size[1] * 1.2), sharex=True,
                                      gridspec_kw=dict(height_ratios=[1, 5]), layout="constrained")
    else:
        fig, ax = plt.subplots(figsize=size, layout="constrained")
        axr = None
    draw_fit(ax, model, res, th_name, sample, region, residual_ax=axr)
    fig.savefig(path, dpi=dpi, facecolor="white")
    plt.close(fig)
    return path


def save_stack_figure(path: str, items: list[tuple[str, RegionModel, FitResult]], th_name=None,
                      region: str = "", dpi: int = 300, gap: float = 0.15, size=(6.5, 6.0)):
    """Stacked comparison of several samples (same region), each normalised to its peak height."""
    matplotlib.use("Agg", force=False)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=size, layout="constrained")
    off = 0.0
    th = theme(th_name)
    for j, (label, model, res) in enumerate(items):
        scale = max(np.max(res.y - res.bg), 1e-12)
        r2 = _scaled(res, 1.0 / scale, -np.min(res.bg) / scale)
        draw_fit(ax, model, r2, th_name, legend=(j == len(items) - 1), show_labels=False, offset=off,
                 legend_kw=dict(loc="upper left", bbox_to_anchor=(1.01, 1.0)))
        i_lo = int(np.argmin(r2.x))
        ax.text(float(r2.x[i_lo]), off + float(r2.bg[i_lo]) + 0.08, label_mathtext(label), ha="right",
                va="bottom", fontsize=11, fontfamily=th["font"])
        off += float(np.max(r2.envelope)) + gap
    ax.set_title(region_mathtext(region), loc="left", fontsize=13, fontfamily=th["font"])
    fig.savefig(path, dpi=dpi, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    return path


def _scaled(res: FitResult, k: float, b: float) -> FitResult:
    import copy
    r = copy.copy(res)
    r.y = res.y * k + b
    r.bg = res.bg * k + b
    r.envelope = res.envelope * k + b
    r.residual = res.residual * k
    r.comp_curves = {n: [l_ * k for l_ in ls] for n, ls in res.comp_curves.items()}
    return r
