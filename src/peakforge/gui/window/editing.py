"""Current spectrum: display, model editing, undo / redo."""
from __future__ import annotations


import numpy as np
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QInputDialog, QTableWidgetItem)

from ... import presets
from ...core.fit import fit as run_fit
from ...core.model import Component, Param, RegionModel
from ...logs import log
from ...schema import SchemaError
from ..i18n import flag_text, tr


class EditMixin:
    def select_key(self, key: str, keep_view: bool = False):
        p = self.project
        self.key = key
        s = p.spectra[key]
        try:
            self.model = p.get_model(key)
        except SchemaError as e:
            self.model = None
            self.fail(f"{tr('model_invalid')}\n{e}")
        self.panel.set_presets(s.region, p.root)
        res = p.result(key) if self.model is not None else None
        self._show(res, keep_view)

    def _show(self, res=None, keep_view=False):
        p, key = self.project, self.key
        s = p.spectra[key]
        sh = p.shift(s.sample)
        prep = None
        if self.model is not None:
            try:
                prep = p.prepared(key, self.model)
                if res is None:
                    res = run_fit(self.model, prep, optimize=False)
            except Exception as e:      # noqa: BLE001 — shown in the log panel; the plot shows the data only
                log.warning("evaluate %s: %s", key, e, exc_info=True)
                self.say(f"evaluate: {e}")
                res = None
        title = f"{p.sample_label(s.sample)} · {s.region}"
        self.plot_title.setText(s.region)
        meta = s.meta or {}
        bits = [p.sample_label(s.sample), f"{tr('shift')} {sh:+.2f} eV"]
        if meta.get("pass_energy"):
            bits.append(f"PE {meta['pass_energy']:g} eV")
        if self.model is not None and self.model.preset:
            bits.append(self.model.preset)
        self.plot_sub.setText("   ·   ".join(bits))
        self.view.theme = p.figure_theme(key, len(self.model.components) if self.model is not None else 8)
        self.view.show_spectrum(s.be + sh, s.cps, title, self.model, prep, res, keep_view)
        self.panel.set_model(self.model, s.region, res.stderr if res is not None else None)
        self._fill_results(res)

    def _fill_results(self, res):
        t = self.res_tab
        if res is None or self.model is None:
            t.setRowCount(0)
            return
        rows = res.summary_rows(self.model)
        cols = [("label", tr("col_label")), ("center", tr("col_center")), ("center_err", "±"),
                ("fwhm", tr("col_fwhm")), ("fwhm_err", "±"), ("area", tr("col_area")), ("area_err", "±"),
                ("fraction", tr("col_frac")), ("fraction_err", "±"), ("fwhm_apparent", tr("col_fwhm_app")),
                ("center2", "4f5/2…"), ("shape", tr("col_shape"))]
        t.setColumnCount(len(cols))
        t.setHorizontalHeaderLabels([c[1] for c in cols])
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, (k, _) in enumerate(cols):
                v = r.get(k)
                txt = "" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
                if k in ("center", "center2") and isinstance(v, float):
                    txt = f"{v:.2f}"
                if k in ("fraction", "fraction_err") and isinstance(v, float):
                    txt = f"{v:.1f}"
                t.setItem(i, j, QTableWidgetItem(txt))
        # quality flags (core.quality): tint the rows of flagged components, red for errors
        flags = getattr(res, "flags", None) or []
        worst = {}
        for f in flags:
            if f.get("component"):
                worst[f["component"]] = "error" if f["level"] == "error" else worst.get(f["component"], "warning")
        for i, r in enumerate(rows):
            lvl = worst.get(r["component"])
            if lvl:
                col = QColor(255, 205, 205) if lvl == "error" else QColor(255, 236, 196)
                for j in range(t.columnCount()):
                    if t.item(i, j) is not None:
                        t.item(i, j).setBackground(col)
                        t.item(i, j).setToolTip("\n".join(flag_text(f) for f in flags
                                                          if f.get("component") == r["component"]))
        t.resizeColumnsToContents()
        approx = "≈" if res.noise == "estimated" else ""
        msg = f"{tr('rms')} {res.rms_pct:.2f} %     χ²ᵣ {approx}{res.chi2_red:.2f}     BIC {res.bic:.1f}"
        n_err = sum(f["level"] == "error" for f in flags)
        if flags:
            msg += f"     {'✖' if n_err else '⚠'} {tr('quality_flags')} {len(flags)}"
        self.metric_lbl.setToolTip("\n".join(("✖ " if f["level"] == "error" else "⚠ ") + flag_text(f) for f in flags))
        self.metric_lbl.setStyleSheet("color: #c0392b; font-weight: bold;" if n_err else "")
        self.metric_lbl.setText(msg + "   ")
        key = (self.key, round(res.bic, 6))
        if flags and getattr(self, "_flags_logged", None) != key:      # once per new result
            self._flags_logged = key
            for f in flags:
                self.say(("✖ " if f["level"] == "error" else "⚠ ") + f"{tr('quality_flags')}: {flag_text(f)}")

    def _store(self, push_undo=True):
        """Save the current model; False when it was refused (invalid: kept in memory only)."""
        if self.key is None or self.model is None:
            return True
        from ... import schema
        s = self.project.spectra[self.key]
        rep = schema.check_model(self.model.to_json(), "model", s, self.project.shift(s.sample))
        if not rep.ok:          # keep the edit in memory; saving it would make the model unloadable
            self.say("⚠ " + tr("model_not_saved") + " " + "; ".join(rep.errors()))
            return False
        if push_undo:
            rec = self.project.get_model_record(self.key)
            self.undo.setdefault(self.key, []).append(rec["model"] if rec else None)
            self.redo[self.key] = []
        self._mark_write()
        self.project.set_model(self.key, self.model)
        self.project.results.pop(self.key, None)
        return True

    def _panel_changed(self):
        self._store()
        self._show(keep_view=True)

    def _canvas_edited(self):
        self._store()
        self._show(keep_view=True)

    def do_undo(self):
        st = self.undo.get(self.key or "", [])
        if not st:
            return
        rec = self.project.get_model_record(self.key)
        self.redo.setdefault(self.key, []).append(rec["model"] if rec else None)
        self._restore(st.pop())

    def do_redo(self):
        st = self.redo.get(self.key or "", [])
        if not st:
            return
        rec = self.project.get_model_record(self.key)
        self.undo.setdefault(self.key, []).append(rec["model"] if rec else None)
        self._restore(st.pop())

    def _restore(self, mjson):
        self._mark_write()
        if mjson is None:
            self.project.delete_model(self.key)
            self.model = None
        else:
            self.model = RegionModel.from_json(mjson)
            self.project.set_model(self.key, self.model)
        self.project.results.pop(self.key, None)
        self._show(keep_view=True)
        self.refresh_tree_status()

    def _preset_requested(self, pid: str):
        if self.key is None:
            return
        if pid == "__add__":
            xl = self.view.ax.get_xlim()
            x = self.view.raw[0]; y = self.view.raw[1]
            m = (x >= min(xl)) & (x <= max(xl))
            self._add_peak_at(float(x[m][np.argmax(y[m])]) if m.any() else float(np.mean(xl)))
            return
        self._store()
        self.model = self.project.new_model(self.key, pid or None)
        self._store(push_undo=False)
        self._show()
        self.refresh_tree_status()

    def _add_peak_at(self, x: float):
        if self.key is None:
            return
        p = self.project
        s = p.spectra[self.key]
        sh = p.shift(s.sample)
        if self.model is None:
            self.model = RegionModel(region=s.region)
            presets._clip_range(self.model, s, sh)
            presets.auto_background(self.model, s, sh)
        else:
            self._store()
        m = self.model
        orb = presets.orbital(s.region) or {}
        name = m.unique_name((s.element or "p") + str(len(m.components) + 1))
        c = Component(name=name, label=name, shape="gl",
                      params=dict(center=Param(x, x - 1.5, x + 1.5), fwhm=Param(1.2, 0.3, 4.0),
                                  m=Param(0.3, 0.0, 1.0, vary=False)))
        if orb.get("split"):
            c.set_doublet(True, orb["split"], orb["ratio"])
            c.sub_labels = tuple(orb.get("sub") or ("", ""))
        keep = {cc.name: cc.params["area"].value for cc in m.components}
        m.components.append(c)
        presets.scale_areas(m, s, sh)
        for cc in m.components:
            if cc.name in keep:
                cc.params["area"].value = keep[cc.name]
        self._store(push_undo=False)
        self._show(keep_view=True)
        self.refresh_tree_status()

    def _remove_comp(self, name: str):
        if self.model is None:
            return
        self._store()
        self.model.components = [c for c in self.model.components if c.name != name]
        for _k, c, pn, prm in self.model.param_items():
            if prm.expr and f"{name}." in prm.expr:
                prm.expr = None
        self._store(push_undo=False)
        self._show(keep_view=True)

    def save_preset(self):
        if self.model is None:
            return
        pid, ok = QInputDialog.getText(self, tr("save_preset"), "ID (a-z, 0-9, _)",
                                       text=(self.model.region.replace(" ", "").lower() + "_custom"))
        if not ok or not pid:
            return
        path = presets.save_user_preset(self.model, pid, pid)
        self.say(f"preset → {path}")
        self.panel.set_presets(self.model.region, self.project.root)
