"""Figures for the in-app help (src/peakforge/docs/images/*.png), shared by the zh and en documents.

Only synthetic spectra and PeakForge's own computations (line shapes, backgrounds, fit, orbital table)
are used; schematic figures say so in the figure. Figure text is English. matplotlib Figure API only.

    python tools/make_help_figures.py
"""
import json
import os
import sys

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
from peakforge.core import background, lineshapes  # noqa: E402
from peakforge.core.fit import fit, prepare  # noqa: E402
from peakforge.core.model import RegionModel  # noqa: E402

OUT = os.path.join(ROOT, "src", "peakforge", "docs", "images")
with open(os.path.join(ROOT, "src", "peakforge", "data", "orbitals.json"), encoding="utf-8") as _f:
    ORB = json.load(_f)["orbitals"]
BLUE, TEAL, ORANGE, GREY, RED = "#2f6f9f", "#2a9d8f", "#d08c34", "#888888", "#b5523b"
RNG = np.random.default_rng(7)


def new(w=6.4, h=3.6, n=1, sharex=False, ratios=None):
    fig = Figure(figsize=(w, h), layout="constrained")
    FigureCanvasAgg(fig)
    if n == 1:
        return fig, fig.add_subplot()
    axs = fig.subplots(n, 1, sharex=sharex, gridspec_kw=dict(height_ratios=ratios) if ratios else None)
    return fig, axs


def be_axis(ax, label=True):
    ax.invert_xaxis()                     # XPS convention: BE increases to the left
    if label:
        ax.set_xlabel("Binding energy (eV)")
    ax.set_yticks([])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=110)
    print("wrote", name)


def with_step(x, peaks, base, step):
    """Peaks + flat base + a Shirley-like step (∝ integrated peak intensity at lower BE)."""
    cum = np.concatenate([[0.0], np.cumsum(0.5 * (peaks[1:] + peaks[:-1]) * np.diff(x))])
    return peaks + base + step * cum


# 1 ---------------------------------------------------------------- energy levels (schematic)
def energy_levels():
    fig, ax = new(6.4, 3.8)
    ax.set_xlim(0, 10)
    ax.set_ylim(-0.6, 10.6)
    ax.axis("off")
    # sample
    ax.add_patch(_rect(0.6, 0, 3.0, 5.0, "#dbe8f2"))
    ax.text(2.1, -0.4, "Sample", ha="center", fontsize=9)
    ax.plot([0.6, 3.6], [4.2, 4.2], color="k", lw=1.2)
    ax.text(0.65, 4.32, "Fermi level $E_F$", fontsize=8)
    ax.plot([0.6, 3.6], [6.0, 6.0], color=GREY, lw=1, ls="--")
    ax.text(2.75, 6.12, "vacuum\nlevel", fontsize=7.5, color=GREY)
    ax.plot([0.6, 3.6], [1.0, 1.0], color=BLUE, lw=2)
    ax.text(0.65, 0.55, "core level", fontsize=8, color=BLUE)
    ax.annotate("", (1.4, 4.2), (1.4, 1.0), arrowprops=dict(arrowstyle="<->", color=BLUE))
    ax.text(1.5, 2.5, "$E_B$", color=BLUE, fontsize=10)
    # photon
    ax.annotate("", (2.6, 1.0), (2.6, 9.6), arrowprops=dict(arrowstyle="<-", color=ORANGE, lw=1.5))
    ax.text(2.7, 8.2, r"$h\nu$", color=ORANGE, fontsize=11)
    # spectrometer
    ax.add_patch(_rect(6.2, 0, 3.0, 5.0, "#efe6d6"))
    ax.text(7.7, -0.4, "Spectrometer", ha="center", fontsize=9)
    ax.plot([3.6, 6.2], [4.2, 4.2], color="k", lw=0.8, ls=":")
    ax.text(4.9, 3.75, "contact: common $E_F$", ha="center", fontsize=7.5)
    ax.plot([6.2, 9.2], [4.2, 4.2], color="k", lw=1.2)
    ax.plot([6.2, 9.2], [8.6, 8.6], color=GREY, lw=1, ls="--")
    ax.text(6.25, 8.2, "vacuum level", fontsize=8, color=GREY)
    ax.annotate("", (8.9, 8.6), (8.9, 4.2), arrowprops=dict(arrowstyle="<->", color=GREY))
    ax.text(8.95, 6.2, r"$\phi_{sp}$", color=GREY, fontsize=10)
    ax.plot([6.2, 9.2], [9.6, 9.6], color=RED, lw=2)
    ax.text(6.25, 9.75, "photoelectron", fontsize=8, color=RED)
    ax.annotate("", (7.6, 9.6), (7.6, 8.6), arrowprops=dict(arrowstyle="<->", color=RED))
    ax.text(7.7, 9.0, "$E_K$ (measured)", color=RED, fontsize=8.5)
    ax.text(5.0, 10.5, r"$E_B = h\nu - E_K - \phi_{sp}$   (relative to $E_F$)", ha="center", fontsize=10)
    ax.text(9.9, -0.55, "schematic, not to scale", ha="right", fontsize=7, color=GREY, style="italic")
    save(fig, "energy_levels.png")


def _rect(x, y, w, h, c):
    from matplotlib.patches import Rectangle
    return Rectangle((x, y), w, h, facecolor=c, edgecolor="none")


# 2 ---------------------------------------------------------------- anatomy of a region (synthetic)
def anatomy():
    """Synthetic transition-metal-oxide 2p region: doublet, shake-up satellites, step, loss tail."""
    x = np.arange(925.0, 970.0, 0.1)
    pk = np.zeros_like(x)
    main = [(933.8, 2.8, 10000), (942.0, 5.0, 5000), (933.8 + 19.9, 3.2, 5000), (962.0, 5.0, 2300)]
    for c, w, a in main:
        pk += a * lineshapes.profile("gl", x, c, w, m=0.3)
    y = with_step(x, pk, 3000, 0.045)
    y = RNG.poisson(y * 2) / 2
    fig, ax = new(6.4, 3.4)
    ax.plot(x, y, "o", ms=2.2, mfc="none", color=BLUE, mew=0.6)
    bg = background.compute("shirley", x, y, 926.0, 969.0)
    ax.plot(x, bg, color=GREY, lw=1, ls="--")
    lab = [(933.8, "2p$_{3/2}$"), (953.7, "2p$_{1/2}$"), (942.0, "shake-up\nsatellite"),
           (962.0, "shake-up\nsatellite")]
    for c, t in lab:
        i = np.argmin(abs(x - c))
        ax.annotate(t, (c, y[i]), (c, y[i] + 1200), ha="center", fontsize=8,
                    arrowprops=dict(arrowstyle="-", color=GREY, lw=0.6))
    ax.text(967.5, bg[-1] - 700, "inelastic\nbackground", fontsize=8, color=GREY, ha="center", va="top")
    ya = y[np.argmin(abs(x - 953.7))] + 2300
    ax.annotate("", (933.8, ya), (953.7, ya), arrowprops=dict(arrowstyle="<->", color=TEAL))
    ax.text(943.75, ya + 250, "spin–orbit splitting", ha="center", fontsize=8, color=TEAL)
    ax.set_ylim(top=y.max() * 1.25)
    be_axis(ax)
    ax.set_ylabel("Intensity")
    ax.set_title("Synthetic Cu(II)-like 2p region (schematic)", fontsize=9, loc="left")
    save(fig, "region_anatomy.png")


# 3 ---------------------------------------------------------------- line shapes
def shapes():
    x = np.linspace(-4, 6, 1001)
    fig, ax = new(6.4, 3.4)
    rows = [("gaussian", {}, "Gaussian", GREY), ("lorentzian", {}, "Lorentzian", ORANGE),
            ("gl", dict(m=0.3), "GL(30)", BLUE), ("ds", dict(alpha=0.12, gamma=0.25), "DS (α=0.12) ⊗ G", RED)]
    for sh, kw, lab, col in rows[1:] + rows[:1]:          # Gaussian last (dashed) so GL(30) does not hide it
        y = lineshapes.profile(sh, x, 0.0, 1.0, **kw)
        ax.plot(x, y / y.max(), color=col, lw=1.4, label=lab, ls="--" if sh == "gaussian" else "-")
    ax.set_xlim(5, -3)
    ax.set_xlabel("BE − centre (eV)")
    ax.set_yticks([])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    ax.set_title("Line shapes, FWHM parameter 1 eV, peak-normalised (DS tail towards higher BE)",
                 fontsize=8.5, loc="left")
    save(fig, "lineshapes.png")


# 4 ---------------------------------------------------------------- spin–orbit doublets from the table
def doublets():
    fig = Figure(figsize=(6.6, 2.6), layout="constrained")
    FigureCanvasAgg(fig)
    axs = fig.subplots(1, 3)
    for ax, (key, w) in zip(axs, (("Si 2p", 0.35), ("Ag 3d", 0.55), ("Au 4f", 0.7))):
        o = ORB[key]
        c, s, r = o["be"], o["split"], o["ratio"]
        x = np.linspace(c - 2.5, c + s + 2.5, 800)
        a = lineshapes.profile("gl", x, c, w, m=0.3)
        b = r * lineshapes.profile("gl", x, c + s, w, m=0.3)
        ax.fill_between(x, a, color=BLUE, alpha=0.35, lw=0)
        ax.fill_between(x, b, color=TEAL, alpha=0.35, lw=0)
        ax.plot(x, a + b, color="k", lw=1)
        sub = o["sub"]
        ax.set_title(f"{key}: Δ = {s:g} eV, {sub[1]}/{sub[0]} = {r:.3g}", fontsize=8)
        be_axis(ax, label=False)
    axs[1].set_xlabel("Binding energy (eV)  ·  widths schematic, splittings from the orbital table")
    save(fig, "doublets.png")


# 5 ---------------------------------------------------------------- backgrounds
def backgrounds():
    """Synthetic Au 4f whose inelastic tail is made with the universal U2 cross section
    (B = 2866 eV², C = 1643 eV²), on a wide window; then linear, Shirley and Tougaard backgrounds."""
    dx = 0.1
    x = np.arange(78.0, 116.0, dx)
    w = ORB["Au 4f"]["split"]
    pk = 8000 * lineshapes.profile("gl", x, 84.0, 0.75, m=0.3)
    pk += 0.75 * 8000 * lineshapes.profile("gl", x, 84.0 + w, 0.75, m=0.3)
    t = np.arange(len(x)) * dx
    k = 2866.0 * t / (1643.0 + t ** 2) ** 2
    loss = np.convolve(pk, k)[: len(x)] * dx            # loss(E) = ∫ K(E − E') pk(E') dE'
    true_bg = 600 + loss
    y = RNG.poisson((pk + true_bg) * 4) / 4
    lo, hi = 80.0, 112.0
    fig, ax = new(6.4, 3.4)
    ax.plot(x, y, "o", ms=1.8, mfc="none", color=BLUE, mew=0.5, label="synthetic Au 4f")
    ax.plot(x, true_bg, color="k", lw=1, ls="--", label="loss tail used to make the data")
    for kind, col, lab in (("linear", GREY, "linear"), ("shirley", ORANGE, "Shirley"),
                           ("tougaard", RED, "Tougaard U2")):
        ax.plot(x, background.compute(kind, x, y, lo, hi), color=col, lw=1.3, label=lab)
    for e in (lo, hi):
        ax.axvline(e, color="k", lw=0.6, ls=":")
    ax.set_ylim(true_bg.min() * 0.8, true_bg.max() * 1.7)
    be_axis(ax)
    ax.legend(frameon=False, fontsize=7.5, loc="upper right")
    ax.set_title("Same data and end points (dotted); y axis cut to show the base", fontsize=8.5, loc="left")
    save(fig, "backgrounds.png")


# 6 ---------------------------------------------------------------- information depth (schematic λ)
def depth():
    d = np.linspace(0, 10, 300)
    lam = 2.0
    fig, ax = new(5.4, 3.2)
    for th, col in ((0, BLUE), (45, TEAL), (70, ORANGE)):
        ax.plot(d, 100 * (1 - np.exp(-d / (lam * np.cos(np.radians(th))))), color=col,
                label=f"θ = {th}° from the normal")
    ax.axhline(95, color=GREY, lw=0.6, ls=":")
    ax.text(9.9, 92, "95 %", ha="right", fontsize=8, color=GREY)
    ax.set_xlabel("Depth d (nm)")
    ax.set_ylabel("Signal from depth < d (%)")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    ax.set_title("I ∝ exp(−d / λ cos θ), λ = 2 nm (schematic)", fontsize=9, loc="left")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    save(fig, "depth.png")


# 7 ---------------------------------------------------------------- residuals: one vs two components
def _model(centres):
    comps = [dict(name=f"p{i}", label=f"p{i}", shape="gl",
                  params=dict(center=dict(value=c, min=c - 1, max=c + 1),
                              fwhm=dict(value=1.2, min=0.5, max=2.5),
                              m=dict(value=0.3, vary=False), area=dict(value=3000, min=0)))
             for i, c in enumerate(centres)]
    return RegionModel.from_json(dict(region="O 1s", components=comps,
                                      background=dict(kind="shirley", lo=526.0, hi=536.0)))


def residuals():
    x = np.arange(525.0, 537.0, 0.1)
    pk = 6000 * lineshapes.profile("gl", x, 530.0, 1.2, m=0.3) + 3000 * lineshapes.profile("gl", x, 531.4, 1.4, m=0.3)
    y = RNG.poisson(with_step(x, pk, 2500, 0.05) * 2) / 2
    fig = Figure(figsize=(6.6, 3.6), layout="constrained")
    FigureCanvasAgg(fig)
    axs = fig.subplots(2, 2, sharex=True, gridspec_kw=dict(height_ratios=(3, 1)))
    for j, cs in enumerate(([530.4], [530.0, 531.4])):
        m = _model(cs)
        prep = prepare(x, y, m, acq_time=2.0)          # counts = 2 s × cps: counting noise known
        r = fit(m, prep, n_starts=3)
        top, bot = axs[0, j], axs[1, j]
        top.plot(r.x, r.y, "o", ms=2, mfc="none", color=BLUE, mew=0.5)
        top.plot(r.x, r.bg, color=GREY, lw=0.8)
        for lines in r.comp_curves.values():
            top.fill_between(r.x, r.bg, r.bg + sum(lines), alpha=0.3, lw=0)
        top.plot(r.x, r.envelope, color="k", lw=1)
        top.set_title(f"{len(cs)} component{'s' if len(cs) > 1 else ''}: χ²ᵣ ≈ {r.chi2_red:.1f}",
                      fontsize=9, loc="left")
        bot.plot(r.x, r.residual, color=RED if j == 0 else GREY, lw=0.8)
        bot.axhline(0, color="k", lw=0.5)
        bot.set_ylabel("resid.", fontsize=8)
        be_axis(top, label=False)
        be_axis(bot)
        top.invert_xaxis()                # sharex: the second inversion would undo the first
    save(fig, "residuals.png")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    energy_levels()
    anatomy()
    shapes()
    doublets()
    backgrounds()
    depth()
    residuals()
