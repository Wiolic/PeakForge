"""PeakForge main window."""
from __future__ import annotations

import json
import os
import time

import numpy as np
from PySide6.QtCore import QFileSystemWatcher, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QHeaderView, QInputDialog, QLabel, QMainWindow,
                               QMessageBox, QPlainTextEdit, QScrollArea, QTableWidget, QTableWidgetItem,
                               QTabWidget, QTreeWidget, QTreeWidgetItem)

from .. import APP_NAME, APP_NAME_ZH, __version__, presets
from ..core.diagnostics import diagnose
from ..core.fit import fit as run_fit
from ..core.model import Component, Param, RegionModel
from ..export.themes import THEMES
from ..io import FILE_FILTER
from ..project import EXT, Project
from . import i18n
from .canvas import SpectrumView
from .dialogs import AgentDialog, BatchDialog, ExportDialog
from .i18n import tr
from .model_panel import ModelPanel
from .workers import submit

ICON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "peakforge.ico")


class MainWindow(QMainWindow):
    def __init__(self, project_path: str | None = None, restart_cb=None):
        super().__init__()
        self.restart_cb = restart_cb
        self.project: Project | None = None
        self.key: str | None = None
        self.model: RegionModel | None = None
        self.undo: dict[str, list] = {}
        self.redo: dict[str, list] = {}
        self._own_write = 0.0
        self._busy = 0
        self.setWindowTitle(f"{APP_NAME} {APP_NAME_ZH} {__version__}")
        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
        self.resize(1500, 900)

        self.view = SpectrumView()
        self.setCentralWidget(self.view)
        self.view.edited.connect(self._canvas_edited)
        self.view.add_peak.connect(self._add_peak_at)
        self.view.remove_comp.connect(self._remove_comp)
        self.view.status.connect(lambda s: self.statusBar().showMessage(s, 3000))

        # left: spectra tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("spectra"), tr("rms")])
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.currentItemChanged.connect(self._tree_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        d = QDockWidget(tr("spectra")); d.setObjectName("spectra"); d.setWidget(self.tree)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, d)

        # right: model panel
        self.panel = ModelPanel()
        self.panel.changed.connect(self._panel_changed)
        self.panel.fit_requested.connect(self.fit_current)
        self.panel.diag_requested.connect(self.diagnose_current)
        self.panel.preset_requested.connect(self._preset_requested)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(self.panel); sa.setMinimumWidth(430)
        d2 = QDockWidget(tr("model")); d2.setObjectName("model"); d2.setWidget(sa)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, d2)

        # bottom: results / diagnostics / quant / log
        self.tabs = QTabWidget()
        self.res_tab = QTableWidget(); self.res_tab.verticalHeader().setVisible(False)
        self.diag_txt = QPlainTextEdit(); self.diag_txt.setReadOnly(True)
        self.quant_tab = QTableWidget(); self.quant_tab.verticalHeader().setVisible(False)
        self.quant_tab.itemChanged.connect(self._rsf_edited)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.tabs.addTab(self.res_tab, tr("results"))
        self.tabs.addTab(self.diag_txt, tr("diagnose"))
        self.tabs.addTab(self.quant_tab, tr("quant"))
        self.tabs.addTab(self.log, tr("log"))
        d3 = QDockWidget(tr("results")); d3.setObjectName("results"); d3.setWidget(self.tabs)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, d3)
        self.resizeDocks([d3], [230], Qt.Orientation.Vertical)
        self.resizeDocks([d], [260], Qt.Orientation.Horizontal)

        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._fs_changed)
        self.watcher.directoryChanged.connect(self._fs_changed)
        self._reload_timer = QTimer(self); self._reload_timer.setSingleShot(True); self._reload_timer.setInterval(400)
        self._reload_timer.timeout.connect(self._external_reload)

        self._build_menus()
        self.view.clear(tr("no_project"))
        self.statusBar().showMessage(tr("hint_canvas"))
        if project_path:
            self.open_project(project_path)

    # ------------------------------------------------------------------ menus
    def _act(self, menu, text, slot, shortcut=None):
        a = QAction(text, self)
        a.triggered.connect(slot)
        if shortcut:
            a.setShortcut(QKeySequence(shortcut))
        menu.addAction(a)
        return a

    def _build_menus(self):
        mb = self.menuBar()
        m = mb.addMenu(tr("menu_file"))
        self._act(m, tr("new_project"), self.new_project, "Ctrl+N")
        self._act(m, tr("open_project"), self.open_project_dialog, "Ctrl+O")
        self._act(m, tr("import"), self.import_files, "Ctrl+I")
        self.recent_menu = m.addMenu(tr("recent"))
        self._fill_recent()
        m.addSeparator()
        self._act(m, tr("quit"), self.close, "Ctrl+Q")

        m = mb.addMenu(tr("menu_analysis"))
        self._act(m, tr("auto_charge"), self.auto_charge)
        self._act(m, tr("set_shift"), self.set_shift)
        m.addSeparator()
        self._act(m, tr("fit"), lambda: self.fit_current(self.panel.starts.value()), "F5")
        self._act(m, tr("fit_all"), self.fit_all, "Shift+F5")
        self._act(m, tr("batch"), self.batch)
        self._act(m, tr("diagnose"), self.diagnose_current, "F6")
        self._act(m, tr("quant"), self.show_quant)
        m.addSeparator()
        self._act(m, tr("undo"), self.do_undo, "Ctrl+Z")
        self._act(m, tr("redo"), self.do_redo, "Ctrl+Y")
        self._act(m, tr("save_preset"), self.save_preset)

        m = mb.addMenu(tr("menu_export"))
        self._act(m, tr("export_all"), self.export, "Ctrl+E")

        m = mb.addMenu(tr("menu_view"))
        ml = m.addMenu(tr("language"))
        g = QActionGroup(self)
        for code, name in (("zh", "中文"), ("en", "English")):
            a = QAction(name, self, checkable=True)
            a.setChecked(i18n.lang() == code)
            a.triggered.connect(lambda _=False, c=code: self.switch_lang(c))
            g.addAction(a); ml.addAction(a)
        mt = m.addMenu(tr("theme"))
        g2 = QActionGroup(self)
        self.theme_actions = {}
        for k, t in THEMES.items():
            a = QAction(t["name_zh"] if i18n.lang() == "zh" else t["name_en"], self, checkable=True)
            a.triggered.connect(lambda _=False, kk=k: self.set_theme(kk))
            g2.addAction(a); mt.addAction(a)
            self.theme_actions[k] = a
        self.theme_actions["ir_blue"].setChecked(True)

        m = mb.addMenu(tr("menu_agent"))
        self._act(m, tr("agent_connect"), lambda: AgentDialog(self.project, self).exec())
        m = mb.addMenu(tr("menu_help"))
        self._act(m, tr("about"), self.about)

        tb = self.addToolBar("main"); tb.setObjectName("toolbar")
        for text, slot in ((tr("open_project"), self.open_project_dialog), (tr("import"), self.import_files),
                           (tr("auto_charge"), self.auto_charge), (tr("fit"), lambda: self.fit_current(self.panel.starts.value())),
                           (tr("fit_all"), self.fit_all), (tr("diagnose"), self.diagnose_current),
                           (tr("export_all"), self.export)):
            a = QAction(text, self); a.triggered.connect(slot); tb.addAction(a)

    def _fill_recent(self):
        self.recent_menu.clear()
        for p in i18n.settings().get("recent", [])[:10]:
            self._act(self.recent_menu, p, lambda _=False, pp=p: self.open_project(pp))

    def _remember(self, path):
        r = [p for p in i18n.settings().get("recent", []) if p != path]
        i18n.save_setting("recent", [path] + r[:9])

    # ------------------------------------------------------------------ logging / busy
    def say(self, msg: str):
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + msg)
        self.statusBar().showMessage(msg.splitlines()[0][:200], 5000)

    def fail(self, msg: str):
        self._set_busy(False)
        self.say("ERROR: " + msg)
        QMessageBox.warning(self, APP_NAME, msg.splitlines()[0][:500])

    def _set_busy(self, on: bool):
        self._busy += 1 if on else -1
        self._busy = max(self._busy, 0)
        if self._busy:
            self.statusBar().showMessage(tr("fitting"))
            self.setCursor(Qt.CursorShape.BusyCursor)
        else:
            self.unsetCursor()

    # ------------------------------------------------------------------ project
    def new_project(self):
        d = QFileDialog.getExistingDirectory(self, tr("new_project"))
        if not d:
            return
        name, ok = QInputDialog.getText(self, tr("new_project"), "Name", text=os.path.basename(d))
        if not ok:
            return
        p = Project.create(d, name or None)
        self.open_project(p.path)

    def open_project_dialog(self):
        f, _ = QFileDialog.getOpenFileName(self, tr("open_project"), "", f"PeakForge (*{EXT})")
        if f:
            self.open_project(f)

    def open_project(self, path: str):
        try:
            self.project = Project.open(path)
        except Exception as e:      # noqa: BLE001
            self.fail(str(e))
            return
        self._remember(self.project.path)
        self.setWindowTitle(f"{APP_NAME} {APP_NAME_ZH} — {self.project.name}")
        th = self.project.settings.get("theme", "ir_blue")
        self.view.theme = th
        if th in self.theme_actions:
            self.theme_actions[th].setChecked(True)
        self._watch()
        self.refresh_tree()
        self.say(f"{self.project.path}: {len(self.project.spectra)} spectra")

    def _watch(self):
        for p in self.watcher.files() + self.watcher.directories():
            self.watcher.removePath(p)
        if self.project:
            self.watcher.addPath(self.project.path)
            md = os.path.join(self.project.root, "models")
            os.makedirs(md, exist_ok=True)
            self.watcher.addPath(md)

    def _fs_changed(self, _path):
        if time.time() < self._own_write:
            return
        self._reload_timer.start()

    def _external_reload(self):
        if self.project is None or time.time() < self._own_write:
            return
        key = self.key
        try:
            self.project.reload()
        except Exception:       # noqa: BLE001
            return
        self.project.results.clear()
        self._watch()
        self.refresh_tree(select=key)
        self.say(tr("reloaded"))

    def _mark_write(self):
        self._own_write = time.time() + 1.5

    def import_files(self):
        if self.project is None:
            self.new_project()
            if self.project is None:
                return
        files, _ = QFileDialog.getOpenFileNames(self, tr("import"), "", FILE_FILTER)
        if not files:
            return
        self._mark_write()
        for f in files:
            try:
                keys = self.project.add_file(f)
                self.say(f"+ {os.path.basename(f)}: {len(keys)} spectra")
            except Exception as e:  # noqa: BLE001
                self.fail(f"{f}: {e}")
        self.refresh_tree()

    # ------------------------------------------------------------------ tree
    def refresh_tree(self, select: str | None = None):
        p = self.project
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        target = None
        for smp in p.samples():
            sh = p.shift(smp)
            it = QTreeWidgetItem([f"{p.sample_label(smp)}   ({tr('shift')} {sh:+.2f} eV)", ""])
            it.setData(0, Qt.ItemDataRole.UserRole, ("sample", smp))
            self.tree.addTopLevelItem(it)
            for k in p.keys(sample=smp):
                s = p.spectra[k]
                rec = p.get_model_record(k)
                rms = ""
                if rec and rec.get("result"):
                    rms = f"{rec['result'].get('rms_pct', 0):.2f}%" + (" *" if rec.get("result_stale") else "")
                elif rec:
                    rms = "…"
                ch = QTreeWidgetItem([("● " if rec else "○ ") + s.region + (f" #{s.index}" if s.index else ""), rms])
                ch.setData(0, Qt.ItemDataRole.UserRole, ("spec", k))
                it.addChild(ch)
                if first is None and not s.is_survey:
                    first = ch
                if k == (select or self.key):
                    target = ch
            it.setExpanded(True)
        self.tree.blockSignals(False)
        (target or first) and self.tree.setCurrentItem(target or first)
        if self.tree.currentItem() is None:
            self.view.clear(tr("no_project") if not p.spectra else "")

    def _tree_changed(self, cur, _prev):
        if cur is None:
            return
        kind, val = cur.data(0, Qt.ItemDataRole.UserRole)
        if kind == "spec":
            self.select_key(val)

    def _tree_menu(self, pos):
        it = self.tree.itemAt(pos)
        if it is None or self.project is None:
            return
        from PySide6.QtWidgets import QMenu
        kind, val = it.data(0, Qt.ItemDataRole.UserRole)
        smp = val if kind == "sample" else self.project.spectra[val].sample
        m = QMenu(self)
        m.addAction(tr("set_shift"), lambda: self.set_shift(smp))
        m.addAction(tr("rename_sample"), lambda: self.rename_sample(smp))
        m.addAction(tr("remove_sample"), lambda: self.remove_sample(smp))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def rename_sample(self, smp):
        t, ok = QInputDialog.getText(self, tr("rename_sample"), tr("label_sample"), text=self.project.sample_label(smp))
        if ok and t:
            self._mark_write()
            self.project.set_sample_label(smp, t)
            self.refresh_tree()

    def remove_sample(self, smp):
        if QMessageBox.question(self, APP_NAME, f"{tr('remove_sample')}: {smp}?") != QMessageBox.StandardButton.Yes:
            return
        self._mark_write()
        self.project.remove_sample(smp)
        self.key = None
        self.refresh_tree()

    # ------------------------------------------------------------------ current spectrum
    def select_key(self, key: str, keep_view: bool = False):
        p = self.project
        self.key = key
        s = p.spectra[key]
        self.model = p.get_model(key)
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
            except Exception as e:  # noqa: BLE001
                self.say(f"evaluate: {e}")
                res = None
        title = f"{p.sample_label(s.sample)} · {s.region}"
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
                ("fraction", tr("col_frac")), ("center2", "4f5/2…"), ("shape", tr("col_shape"))]
        t.setColumnCount(len(cols))
        t.setHorizontalHeaderLabels([c[1] for c in cols])
        t.setRowCount(len(rows))
        for i, r in enumerate(rows):
            for j, (k, _) in enumerate(cols):
                v = r.get(k)
                txt = "" if v is None else (f"{v:.4g}" if isinstance(v, float) else str(v))
                if k in ("center", "center2") and isinstance(v, float):
                    txt = f"{v:.2f}"
                if k == "fraction" and isinstance(v, float):
                    txt = f"{v:.1f}"
                t.setItem(i, j, QTableWidgetItem(txt))
        t.resizeColumnsToContents()
        msg = f"{tr('rms')}: {res.rms_pct:.2f} %   χ²ᵣ {res.chi2_red:.2f}   BIC {res.bic:.1f}"
        if res.bound_hits:
            msg += "   ⚠ " + ", ".join(res.bound_hits)
        self.statusBar().showMessage(msg)

    def _store(self, push_undo=True):
        if self.key is None or self.model is None:
            return
        if push_undo:
            rec = self.project.get_model_record(self.key)
            self.undo.setdefault(self.key, []).append(rec["model"] if rec else None)
            self.redo[self.key] = []
        self._mark_write()
        self.project.set_model(self.key, self.model)
        self.project.results.pop(self.key, None)

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

    def refresh_tree_status(self):
        it = self.tree.currentItem()
        if it is None or self.key is None:
            return
        rec = self.project.get_model_record(self.key)
        s = self.project.spectra[self.key]
        it.setText(0, ("● " if rec else "○ ") + s.region + (f" #{s.index}" if s.index else ""))
        if rec and rec.get("result"):
            it.setText(1, f"{rec['result'].get('rms_pct', 0):.2f}%" + (" *" if rec.get("result_stale") else ""))

    # ------------------------------------------------------------------ model building
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

    # ------------------------------------------------------------------ fitting
    def fit_current(self, n_starts: int = 3):
        if self.key is None:
            return
        if self.model is None:
            self.model = self.project.new_model(self.key)
        else:
            self._store()
        key, model = self.key, self.model.copy()
        self._set_busy(True)

        def job():
            return self.project.fit(key, model, n_starts=n_starts, save=False)

        def done(out):
            self._set_busy(False)
            m, r = out
            self._mark_write()
            self.project.set_model(key, m, r)
            if self.key == key:
                self.model = m
                self._show(r, keep_view=True)
                self.refresh_tree_status()
            self.say(f"{key}: RMS {r.rms_pct:.2f} %  " + "  ".join(f"{k} {v:.1f}%" for k, v in r.fractions.items()))
        submit(job, on_done=done, on_fail=self.fail)

    def fit_all(self):
        if self.project is None:
            return
        keys = self.project.keys(narrow_only=True)
        n = self.panel.starts.value()
        self._set_busy(True)
        self._mark_write()

        def job():
            out = []
            for k in keys:
                try:
                    m, r = self.project.fit(k, n_starts=n)
                    out.append((k, r.rms_pct, None))
                except Exception as e:     # noqa: BLE001
                    out.append((k, None, str(e)))
            return out

        def done(out):
            self._set_busy(False)
            self._mark_write()
            for k, rms, err in out:
                self.say(f"{k}: " + (f"RMS {rms:.2f} %" if err is None else "ERROR " + err))
            self.refresh_tree(select=self.key)
        submit(job, on_done=done, on_fail=self.fail)

    def diagnose_current(self):
        if self.key is None or self.model is None:
            return
        key, model = self.key, self.model.copy()
        self._set_busy(True)
        self.tabs.setCurrentWidget(self.diag_txt)
        self.diag_txt.setPlainText(tr("fitting"))

        def job():
            prep = self.project.prepared(key, model)
            r = run_fit(model, prep, n_starts=1)
            return diagnose(model, prep, r, deep=True)

        def done(d):
            self._set_busy(False)
            lines = [f"{tr('rms')}: {d['rms_pct']:.2f} %    χ²ᵣ = {d['chi2_red']:.2f}    BIC = {d['bic']:.1f}", ""]
            if d["warnings"]:
                lines += [tr("warnings") + ":"] + ["  ⚠ " + w for w in d["warnings"]] + [""]
            lines.append("ΔBIC (remove component → refit):")
            for s in d.get("significance", []):
                lines.append(f"  {s['label']:<22} ΔBIC {s['d_bic']:+8.1f}   ΔRMS {s['d_rms']:+.2f} %   {s['verdict']}")
            st = d.get("stability", {})
            if st:
                lines.append("")
                lines.append(f"Multi-start ({st['n_equivalent']}/{st['n_starts']} equivalent solutions):")
                for k, v in st["fractions"].items():
                    lines.append(f"  {k:<22} {v['mean']:.1f} ± {v['std']:.1f} %  [{v['min']:.1f}–{v['max']:.1f}]")
            if d["correlations"]:
                lines.append("")
                lines.append("|corr| ≥ 0.95:")
                for c in d["correlations"]:
                    lines.append(f"  {c['a']} ~ {c['b']}: {c['r']:+.3f}")
            self.diag_txt.setPlainText("\n".join(lines))
        submit(job, on_done=done, on_fail=self.fail)

    def batch(self):
        if self.key is None or self.model is None:
            return
        self._store()
        dlg = BatchDialog(self.project, self.key, self)
        if not dlg.exec():
            return
        v = dlg.values()
        src = self.key
        self._set_busy(True)

        def done(rows):
            self._set_busy(False)
            self._mark_write()
            for r in rows:
                self.say(f"{r['key']}: RMS {r['rms_pct']:.2f} %  " +
                         "  ".join(f"{k} {x:.1f}%" for k, x in r["fractions"].items()))
            self.refresh_tree(select=src)
        self._mark_write()
        submit(self.project.batch_apply, src, v["targets"], v["fix"], v["n_starts"], on_done=done, on_fail=self.fail)

    # ------------------------------------------------------------------ charge / quant
    def auto_charge(self):
        if self.project is None:
            return
        self._mark_write()
        out = self.project.auto_charge()
        self.say("C 1s → " + str(self.project.settings.get("charge_ref", 284.8)) + " eV: " +
                 ", ".join(f"{k} {v:+.2f}" for k, v in out.items()))
        self.refresh_tree()

    def set_shift(self, sample: str | None = None):
        if self.project is None:
            return
        if sample is None:
            if self.key is None:
                return
            sample = self.project.spectra[self.key].sample
        v, ok = QInputDialog.getDouble(self, tr("set_shift"), f"{sample} (eV)", self.project.shift(sample), -50, 50, 3)
        if ok:
            self._mark_write()
            self.project.set_shift(sample, v)
            self.refresh_tree()

    def show_quant(self):
        if self.project is None:
            return
        q = self.project.quantify()
        t = self.quant_tab
        t.blockSignals(True)
        cols = [tr("sample"), tr("region"), tr("col_area"), "src", tr("rsf"), tr("at_pct")]
        t.setColumnCount(len(cols)); t.setHorizontalHeaderLabels(cols); t.setRowCount(len(q))
        for i, e in enumerate(q):
            vals = [self.project.sample_label(e["sample"]), e["region"], f"{e['area']:.4g}", e["area_source"],
                    "" if e.get("rsf") is None else f"{e['rsf']:.4g}",
                    "" if e.get("at_pct") is None else f"{e['at_pct']:.2f}"]
            for j, v in enumerate(vals):
                it = QTableWidgetItem(v)
                if j != 4:
                    it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                else:
                    it.setData(Qt.ItemDataRole.UserRole, e["region"])
                t.setItem(i, j, it)
        t.resizeColumnsToContents()
        t.blockSignals(False)
        self.tabs.setCurrentWidget(t)

    def _rsf_edited(self, it):
        if it.column() != 4:
            return
        try:
            v = float(it.text())
        except ValueError:
            return
        self._mark_write()
        self.project.set_rsf(it.data(Qt.ItemDataRole.UserRole), v)
        QTimer.singleShot(0, self.show_quant)

    # ------------------------------------------------------------------ export / view
    def export(self):
        if self.project is None:
            return
        dlg = ExportDialog(self.project, self)
        if not dlg.exec():
            return
        v = dlg.values()
        from ..export.exporter import export_all
        self._set_busy(True)

        def done(r):
            self._set_busy(False)
            self.say(f"export → {r['out_dir']}  ({r['n']} fits, {len(r['figures'])} figures)")
            o = r.get("origin")
            if o:
                if o["mode"] == "originpro":
                    self.say(f"Origin: {o['opju']}")
                else:
                    self.say(tr("origin_missing") + " " + o["hint"])
            if r.get("xlsx"):
                self.say(f"Excel: {r['xlsx']}")
            os.startfile(r["out_dir"]) if hasattr(os, "startfile") else None
        submit(export_all, self.project, None, v["out_dir"], v["theme"], v["formats"], v["dpi"],
               on_done=done, on_fail=self.fail)

    def set_theme(self, k):
        self.view.theme = k
        if self.project:
            self._mark_write()
            self.project.settings["theme"] = k
            self.project.save()
        self.view.redraw()

    def switch_lang(self, code):
        if code == i18n.lang():
            return
        i18n.set_lang(code)
        if self.restart_cb:
            self.restart_cb(self.project.path if self.project else None)

    def about(self):
        QMessageBox.about(self, APP_NAME, f"<h3>{APP_NAME} {APP_NAME_ZH} {__version__}</h3>"
                          "<p>XPS analysis · SPE/VMS/CSV/Excel · peak fitting with constraints · "
                          "diagnostics · Origin export · MCP agent interface.</p>"
                          "<p>MIT License · <a href='https://github.com/Wiolic/PeakForge'>github.com/Wiolic/PeakForge</a></p>")
