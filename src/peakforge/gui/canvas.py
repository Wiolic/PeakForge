"""Interactive spectrum plot.

  * drag a component's top marker  -> move centre (x) and scale area (height)
  * drag a dashed vertical line    -> background low / high end
  * right click                    -> context menu (add peak here, set background end, remove component)
  * mouse wheel                    -> zoom BE axis around cursor; double click -> reset view
"""
from __future__ import annotations

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from PySide6.QtCore import Signal
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QVBoxLayout, QWidget

from ..core.fit import FitResult, Prepared, fit
from ..core.model import RegionModel
from ..export.themes import comp_color, label_mathtext, region_mathtext, rgb01, theme
from .i18n import tr


class SpectrumView(QWidget):
    edited = Signal()                 # model changed by mouse (after release)
    add_peak = Signal(float)          # BE
    remove_comp = Signal(str)
    status = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.fig = Figure(figsize=(7, 5), facecolor="white", layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toolbar)
        lay.addWidget(self.canvas, 1)
        gs = self.fig.add_gridspec(2, 1, height_ratios=[1, 5])
        self.ax_r = self.fig.add_subplot(gs[0])
        self.ax = self.fig.add_subplot(gs[1], sharex=self.ax_r)
        self.theme = "ir_blue"
        self.model: RegionModel | None = None
        self.prep: Prepared | None = None
        self.res: FitResult | None = None
        self.raw = None          # (x, y) whole spectrum, charge-corrected
        self.title = ""
        self._drag = None
        self._markers = {}
        self._xlim = None
        self.canvas.mpl_connect("button_press_event", self._press)
        self.canvas.mpl_connect("motion_notify_event", self._motion)
        self.canvas.mpl_connect("button_release_event", self._release)
        self.canvas.mpl_connect("scroll_event", self._scroll)

    # ------------------------------------------------------------------ data
    def show_spectrum(self, x, y, title: str, model: RegionModel | None, prep: Prepared | None,
                      res: FitResult | None, keep_view: bool = False):
        self.raw = (np.asarray(x), np.asarray(y))
        self.title, self.model, self.prep, self.res = title, model, prep, res
        if not keep_view:
            self._xlim = None
        self.redraw()

    def clear(self, msg: str = ""):
        self.raw = None
        self.model = self.prep = self.res = None
        self.ax.clear(); self.ax_r.clear()
        self.ax.text(0.5, 0.5, msg, ha="center", va="center", transform=self.ax.transAxes, color="0.4")
        self.ax.set_axis_off(); self.ax_r.set_axis_off()
        self.canvas.draw_idle()

    def redraw(self):
        ax, axr = self.ax, self.ax_r
        if self._xlim is None and ax.has_data() and self.raw is not None:
            pass
        cur = ax.get_xlim() if self._xlim is not None else None
        ax.clear(); axr.clear()
        ax.set_axis_on(); axr.set_axis_on()
        th = theme(self.theme)
        self._markers = {}
        if self.raw is None:
            self.canvas.draw_idle()
            return
        x, y = self.raw
        ax.plot(x, y, "o", ms=3.5, mfc="none", mec=rgb01(th["data"]), mew=0.8, label="Measured", zorder=4)
        if self.res is not None and self.model is not None:
            r, m = self.res, self.model
            o = np.argsort(r.x)
            xs, bg = r.x[o], r.bg[o]
            for i, c in enumerate(m.components):
                col = rgb01(comp_color(th, i, c.color))
                lines = r.comp_curves.get(c.name)
                if lines is None:
                    continue
                tot = np.sum(lines, axis=0)[o]
                ax.fill_between(xs, bg, bg + tot, color=col, alpha=th["fill_alpha"] + 0.1, lw=0,
                                label=label_mathtext(c.label or c.name))
                ax.plot(xs, bg + tot, color=col, lw=1.0)
                # draggable marker at the main line's top
                main = lines[0][o]
                j = int(np.argmax(main))
                mk, = ax.plot([xs[j]], [bg[j] + tot[j]], "D", ms=7, mfc=col, mec="k", mew=0.6, zorder=6,
                              picker=6)
                self._markers[c.name] = (mk, xs[j], bg[j] + tot[j])
            ax.plot(xs, bg, color=rgb01(th["background"]), lw=1.4, label="Background")
            ax.plot(xs, r.envelope[o], color=rgb01(th["envelope"]), lw=1.6, label="Fit envelope")
            axr.axhline(0, color="0.7", lw=0.8)
            axr.plot(xs, r.residual[o], color=rgb01(th["envelope"]), lw=0.8)
            axr.text(0.01, 0.9, f"{tr('rms')} {r.rms_pct:.2f} %", transform=axr.transAxes, va="top", fontsize=8,
                     color="0.3")
            b = m.background
            lo = b.lo if b.lo is not None else xs.min()
            hi = b.hi if b.hi is not None else xs.max()
            self._bg_lines = (ax.axvline(lo, color="0.45", ls="--", lw=1, picker=5),
                              ax.axvline(hi, color="0.45", ls="--", lw=1, picker=5))
            if m.fit_range:
                a, b2 = sorted(m.fit_range)
                ax.axvspan(x.min(), a, color="0.93", zorder=0)
                ax.axvspan(b2, x.max(), color="0.93", zorder=0)
        ax.set_yticks([])
        axr.set_yticks([])
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
            axr.spines[s].set_visible(False)
        axr.tick_params(labelbottom=False)
        ax.set_xlabel("Binding energy (eV)")
        ax.set_ylabel("Intensity (a.u.)")
        ax.set_title(region_mathtext(self.title.split(" · ")[-1]) + "   " + " · ".join(self.title.split(" · ")[:-1]),
                     loc="left", fontsize=10)
        ax.legend(frameon=False, fontsize=8, loc="upper left")
        if cur is not None:
            ax.set_xlim(cur)
        else:
            ax.set_xlim(x.max(), x.min())
            self._xlim = ax.get_xlim()
        self.canvas.draw_idle()

    # ------------------------------------------------------------------ interaction
    def _hit_marker(self, ev):
        best, bd = None, 12.0
        for name, (mk, mx, my) in self._markers.items():
            px, py = self.ax.transData.transform((mx, my))
            d = np.hypot(px - ev.x, py - ev.y)
            if d < bd:
                best, bd = name, d
        return best

    def _hit_bgline(self, ev):
        if not hasattr(self, "_bg_lines") or self.model is None:
            return None
        for which, ln in zip(("lo", "hi"), self._bg_lines):
            lx = ln.get_xdata()[0]
            px, _ = self.ax.transData.transform((lx, 0))
            if abs(px - ev.x) < 6:
                return which
        return None

    def _press(self, ev):
        if ev.inaxes is not self.ax or self.toolbar.mode:
            return
        if ev.button == 3:
            self._context(ev)
            return
        if ev.dblclick:
            self._xlim = None
            self.redraw()
            return
        if ev.button != 1 or self.model is None:
            return
        name = self._hit_marker(ev)
        if name:
            c = self.model.comp(name)
            self._drag = ("comp", name, c.params["center"].value, ev.xdata, self._markers[name][2])
            return
        which = self._hit_bgline(ev)
        if which:
            self._drag = ("bg", which)

    def _motion(self, ev):
        if self._drag is None or ev.inaxes is not self.ax or ev.xdata is None:
            return
        m = self.model
        if self._drag[0] == "comp":
            _, name, c0, x0, y_top = self._drag
            c = m.comp(name)
            p = c.params["center"]
            if not p.expr:
                p.value = float(np.clip(c0 + (ev.xdata - x0), p.min, p.max))
            a = c.params["area"]
            if not a.expr and self.res is not None:
                bg_at = float(np.interp(ev.xdata, np.sort(self.res.x), self.res.bg[np.argsort(self.res.x)]))
                old_h = max(y_top - bg_at, 1e-9)
                new_h = max(ev.ydata - bg_at, 0.0)
                a.value = max(a.value * new_h / old_h, 0.0)
                self._drag = ("comp", name, c0, x0, max(ev.ydata, bg_at + 1e-9))
            self.status.emit(f"{c.label}: {p.value:.2f} eV")
        else:
            which = self._drag[1]
            if which == "lo":
                m.background.lo = float(ev.xdata)
            else:
                m.background.hi = float(ev.xdata)
            self.status.emit(f"background {which}: {ev.xdata:.2f} eV")
        self._live_update()

    def _release(self, ev):
        if self._drag is not None:
            self._drag = None
            self.edited.emit()

    def _live_update(self):
        if self.prep is None or self.model is None or self.raw is None:
            return
        from ..core.fit import prepare
        x, y = self.raw
        try:
            self.prep = prepare(x, y, self.model, 0.0)
            self.res = fit(self.model, self.prep, optimize=False)
        except Exception:        # noqa: BLE001
            return
        self.redraw()

    def _scroll(self, ev):
        if ev.inaxes not in (self.ax, self.ax_r) or ev.xdata is None:
            return
        lo, hi = self.ax.get_xlim()
        k = 0.85 if ev.button == "up" else 1 / 0.85
        x = ev.xdata
        self.ax.set_xlim(x + (lo - x) * k, x + (hi - x) * k)
        self._xlim = self.ax.get_xlim()
        self.canvas.draw_idle()

    def _context(self, ev):
        menu = QMenu(self)
        x = float(ev.xdata)
        menu.addAction(tr("add_peak_here", x=x), lambda: self.add_peak.emit(x))
        if self.model is not None:
            def set_lo():
                self.model.background.lo = x
                self.edited.emit()

            def set_hi():
                self.model.background.hi = x
                self.edited.emit()
            menu.addSeparator()
            menu.addAction(tr("set_bg_lo", x=x), set_lo)
            menu.addAction(tr("set_bg_hi", x=x), set_hi)
            name = self._hit_marker(ev)
            if name:
                menu.addSeparator()
                menu.addAction(tr("remove_comp", n=self.model.comp(name).label), lambda: self.remove_comp.emit(name))
        menu.exec(QCursor.pos())
