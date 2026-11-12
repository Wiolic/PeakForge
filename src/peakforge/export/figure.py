"""Matplotlib rendering in the project theme (PNG / TIFF / SVG / PDF) and for the GUI canvas."""
from __future__ import annotations

import logging

import matplotlib
import numpy as np

from ..core.fit import FitResult
from ..core.model import RegionModel
from .themes import comp_color, label_mathtext, region_mathtext, rgb01, theme
from ..logs import log

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)
# superscripts / italics in labels use the same sans font as the text (Arial-like, as in Origin)
matplotlib.rcParams.update({"mathtext.fontset": "custom", "mathtext.rm": "Arial",
                            "mathtext.it": "Arial:italic", "mathtext.bf": "Arial:bold"})


def style_axes(ax, th: dict, fs: float = 12):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_linewidth(1.0)
    ax.set_yticks([])
    ax.tick_params(axis="x", direction="out", width=1.0, length=4, labelsize=fs + 0.5)
    ax.tick_params(axis="x", which="minor", direction="out", width=1.0, length=3)
    from matplotlib.ticker import AutoMinorLocator, MultipleLocator
    lo, hi = sorted(ax.get_xlim())
    ax.xaxis.set_major_locator(MultipleLocator(5 if hi - lo > 9 else (2 if hi - lo > 4 else 1)))
    ax.xaxis.set_minor_locator(AutoMinorLocator(2))
    ax.set_xlabel("Binding energy (eV)", fontsize=fs + 1, fontfamily=th["font"])
    ax.set_ylabel("Intensity (a.u.)", fontsize=fs + 1, fontfamily=th["font"])
    for lab in ax.get_xticklabels():
        lab.set_fontfamily(th["font"])


def _darken(c, k=0.28):
    return tuple(max(0.0, v * (1 - k)) for v in c)


def _fit_ylim(ax, res, o, x, leg, fs):
    """Y limits so that the spectrum fills the panel while the top-left legend and the bottom-left
    region/sample label stay clear of the data. The legend box is MEASURED (renderer), not guessed."""
    ymin = float(min(res.y.min(), res.bg.min()))
    ymax = float(max(res.y.max(), res.envelope.max()))
    span = ymax - ymin or 1.0
    try:
        h_in = ax.get_position().height * ax.figure.get_figheight()
    except Exception:       # noqa: BLE001 — layout query on a figure without canvas
        log.debug("figure height unknown, using 3 in", exc_info=True)
        h_in = 3.0
    line = fs * 1.32 / 72 / max(h_in, 0.5)
    f_lab, f_lab_w = min(0.45, 2.6 * line + 0.05), 0.35      # label: height / width fractions
    f_leg_h, f_leg_w = 0.0, 0.0
    if leg is not None:
        try:
            r_ = ax.figure.canvas.get_renderer()
            bb = leg.get_window_extent(r_).transformed(ax.transAxes.inverted())
            f_leg_h, f_leg_w = 1.0 - bb.y0 + 0.03, bb.x1 + 0.03
        except Exception:   # noqa: BLE001 — renderer not available
            log.debug("legend extent unknown, using defaults", exc_info=True)
            f_leg_h, f_leg_w = 0.45, 0.4
    xr = x.max() - x.min()
    yy = np.maximum(res.y[o], res.envelope[o])
    under_leg = x >= x.max() - f_leg_w * xr          # reversed axis: left = high BE
    under_lab = x >= x.max() - f_lab_w * xr
    top_leg = float(yy[under_leg].max()) if under_leg.any() else ymin
    bot_lab = float(min(yy[under_lab].min(), res.bg[o][under_lab].min())) if under_lab.any() else ymin
    lo_y, hi_y = ymin - 0.25 * span, ymax + 0.06 * span
    for _ in range(4):
        if f_leg_h:
            hi_y = max(ymax + 0.06 * span, lo_y + (top_leg - lo_y) / max(1e-9, 1 - f_leg_h))
        lo_y = min(ymin - 0.04 * span, bot_lab - f_lab * (hi_y - lo_y))
    ax.set_ylim(lo_y, hi_y)


def draw_fit(ax, model: RegionModel, res: FitResult, th_name: str | None = None, sample: str = "",
             region: str = "", legend: bool = True, residual_ax=None, fs: float = 12,
             offset: float = 0.0, show_labels: bool = True, legend_kw: dict | None = None,
             label_style: str = "stacked"):
    """Publication style: hollow data circles, dark background line, envelope, each component as a
    translucent fill with a same-hue darker outline; legend top-left, region/sample bottom-left.
    label_style: 'stacked' ('Ir 4f' over 'Sample') or 'inline' ('Sample   O 1s')."""
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    th = theme(th_name)
    x = res.x
    o = np.argsort(x)
    x = x[o]
    bg = res.bg[o] + offset
    lw = th["line_width"]
    ms = th["data_size"] * 0.55 * min(1.0, max(0.6, fs / 11))
    handles = [Line2D([], [], ls="none", marker="o", ms=ms, mfc="none",
                      mec=rgb01(th["data"]), mew=1.2, label="Measured"),
               Line2D([], [], color=rgb01(th["background"]), lw=lw, label="Background"),
               Line2D([], [], color=rgb01(th["envelope"]), lw=lw, label="Fit envelope")]
    patches = {}
    for i, c in enumerate(model.components):
        col = rgb01(comp_color(th, i, c.color))
        edge = _darken(col)
        tot = np.sum(res.comp_curves[c.name], axis=0)[o]
        ax.fill_between(x, bg, bg + tot, color=col, alpha=th["fill_alpha"], lw=0)
        ax.plot(x, bg + tot, color=edge, lw=lw * 0.6, alpha=0.9)
        patches[c.name] = Patch(facecolor=(*col, th["fill_alpha"] + 0.15), edgecolor=edge, lw=0.8,
                                label=label_mathtext(c.label or c.name))
    handles += [patches[c.name] for c in model.legend_components()]
    ax.plot(x, bg, color=rgb01(th["background"]), lw=lw)
    ax.plot(x, res.envelope[o] + offset, color=rgb01(th["envelope"]), lw=lw)
    ax.plot(x, res.y[o] + offset, "o", ms=ms, mfc="none", mec=rgb01(th["data"]),
            mew=0.9, zorder=5)
    ax.set_xlim(x.max(), x.min())
    style_axes(ax, th, fs)
    leg = None
    if legend:
        kw = dict(frameon=False, loc="upper left", prop={"family": th["font"], "size": fs},
                  handlelength=1.6, handleheight=0.8, labelspacing=0.25, borderaxespad=0.3)
        kw.update(legend_kw or {})
        leg = ax.legend(handles=handles, **kw)
    if show_labels and offset == 0.0:
        _fit_ylim(ax, res, o, x, leg, fs)
    if show_labels:
        reg = region_mathtext(region or model.region)
        smp = label_mathtext(sample) if sample else ""
        if label_style == "inline":
            txt = f"{smp}   {reg}" if smp else reg
        else:
            txt = reg + ("\n" + smp if smp else "")
        ax.text(0.03, 0.04, txt, transform=ax.transAxes, ha="left", va="bottom",
                fontsize=fs + 1, fontfamily=th["font"], linespacing=1.5)
    if residual_ax is not None:
        residual_ax.axhline(0, color="0.6", lw=0.8)
        residual_ax.plot(x, res.residual[o], color=rgb01(th["envelope"]), lw=0.8)
        residual_ax.set_xlim(x.max(), x.min())
        residual_ax.set_yticks([])
        for s in ("top", "right"):
            residual_ax.spines[s].set_visible(False)
        residual_ax.tick_params(labelbottom=False)


def _figure(figsize):
    """A pyplot-free Figure with an Agg canvas: safe to build in a worker thread (no global figure registry,
    no backend switch)."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    fig = Figure(figsize=figsize, layout="constrained")
    FigureCanvasAgg(fig)
    return fig


def save_panel_figure(path: str, panels: list[dict], ncols: int = 2, panel_size=(3.7, 2.9),
                      dpi: int = 300, letters: bool = True, fs: float = 8.0):
    """Multi-panel figure, (a), (b), … in reading order.
    panels: [{"model", "result", "theme", "sample", "region", "label_style"}]."""
    n = len(panels)
    ncols = max(1, min(ncols, n))
    nrows = (n + ncols - 1) // ncols
    fig = _figure(figsize=(panel_size[0] * ncols, panel_size[1] * nrows))
    axs = fig.subplots(nrows, ncols, squeeze=False)
    fig.get_layout_engine().set(w_pad=0.12, h_pad=0.1, wspace=0.08, hspace=0.12)
    for i, ax in enumerate(axs.ravel()):
        if i >= n:
            ax.set_axis_off()
            continue
        pn = panels[i]
        draw_fit(ax, pn["model"], pn["result"], pn.get("theme"), pn.get("sample", ""), pn.get("region", ""),
                 fs=fs, label_style=pn.get("label_style", "stacked"))
        if letters:
            th = theme(pn.get("theme"))
            ax.text(-0.13, 1.02, f"({chr(97 + i)})", transform=ax.transAxes, ha="left", va="bottom",
                    fontsize=fs + 3, fontfamily=th["font"])
    fig.savefig(path, dpi=dpi, facecolor="white")
    return path


def save_fit_figure(path: str, model: RegionModel, res: FitResult, th_name: str | None = None,
                    sample: str = "", region: str = "", dpi: int = 300, size=(5.0, 4.0),
                    residual: bool = False, transparent: bool = False):
    if residual:
        fig = _figure(figsize=(size[0], size[1] * 1.2))
        axr, ax = fig.subplots(2, 1, sharex=True, gridspec_kw=dict(height_ratios=[1, 5]))
    else:
        fig = _figure(figsize=size)
        ax = fig.subplots()
        axr = None
    draw_fit(ax, model, res, th_name, sample, region, residual_ax=axr)
    fig.savefig(path, dpi=dpi, facecolor="none" if transparent else "white", transparent=transparent)
    return path


def save_stack_figure(path: str, items: list[tuple[str, RegionModel, FitResult]], th_name=None,
                      region: str = "", dpi: int = 300, gap: float = 0.15, size=(6.5, 6.0)):
    """Stacked comparison of several samples (same region), each normalised to its peak height."""
    fig = _figure(figsize=size)
    ax = fig.subplots()
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
