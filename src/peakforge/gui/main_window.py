"""PeakForge main window."""
from __future__ import annotations

import os
import time

import numpy as np
from PySide6.QtCore import QFileSystemWatcher, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPixmap
from PySide6.QtWidgets import (QFileDialog, QFrame, QHBoxLayout, QHeaderView, QInputDialog, QLabel,
                               QMainWindow, QMessageBox, QPlainTextEdit, QScrollArea, QSplitter, QTableWidget,
                               QTableWidgetItem, QTabWidget, QToolButton, QTreeWidget, QTreeWidgetItem,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, CREDIT, DISCLAIMER_EN, DISCLAIMER_ZH, __version__, presets
from ..core.diagnostics import diagnose
from ..core.fit import fit as run_fit
from ..core.model import Component, Param, RegionModel
from ..export.themes import theme_id
from ..io import FILE_FILTER, ReadError
from ..io.registry import TableReader
from ..logs import log
from ..schema import SchemaError
from ..project import EXT, Project
from . import i18n
from .canvas import SpectrumView
from .dialogs import AgentDialog, BatchDialog, ExportDialog
from .i18n import tr
from .model_panel import ModelPanel
from .palette import PalettePicker
from .style import C, icon


def _dot(color: str, d: int = 10) -> QIcon:
    pm = QPixmap(d * 2, d * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, d * 2 - 8, d * 2 - 8)
    p.end()
    return QIcon(pm)


def _card(title, margins=(12, 10, 12, 10)):
    f = QFrame(); f.setObjectName("card")
    lay = QVBoxLayout(f); lay.setContentsMargins(*margins); lay.setSpacing(8)
    if title:
        t = QLabel(title); t.setObjectName("cardTitle")
        if margins[0] == 0:
            t.setContentsMargins(14, 0, 14, 0)
        lay.addWidget(t)
    return f, lay
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
        self.setWindowTitle(f"{APP_NAME} {__version__}")
        if os.path.exists(ICON):
            self.setWindowIcon(QIcon(ICON))
        self.resize(1500, 900)

        root = QWidget(); root.setObjectName("root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # ---- top bar: brand + main actions + palette
        top = QFrame(); top.setObjectName("topbar")
        tl = QHBoxLayout(top); tl.setContentsMargins(14, 8, 14, 8); tl.setSpacing(4)
        logo = QLabel()
        if os.path.exists(ICON):
            logo.setPixmap(QIcon(ICON).pixmap(26, 26))
        brand = QLabel(APP_NAME); brand.setObjectName("brand")
        credit = QLabel(CREDIT); credit.setObjectName("credit")
        bcol = QVBoxLayout(); bcol.setSpacing(0); bcol.setContentsMargins(0, 0, 0, 0)
        brow = QHBoxLayout(); brow.setSpacing(6)
        self.brand_sub = QLabel(""); self.brand_sub.setObjectName("brandSub")
        brow.addWidget(brand); brow.addWidget(self.brand_sub); brow.addStretch(1)
        bcol.addLayout(brow); bcol.addWidget(credit)
        tl.addWidget(logo); tl.addSpacing(6); tl.addLayout(bcol); tl.addSpacing(22)
        self.panel = ModelPanel()
        self.tool = {}
        for key, ic, text, slot, primary in (
                ("open", "folder", tr("open_project"), self.open_project_dialog, False),
                ("import", "import", tr("import"), self.import_files, False),
                ("charge", "target", tr("auto_charge").split(" (")[0], self.auto_charge, False),
                ("fit", "play", tr("fit"), lambda: self.fit_current(self.panel.starts.value()), True),
                ("fit_all", "layers", tr("fit_all"), self.fit_all, False),
                ("diag", "pulse", tr("diagnose"), self.diagnose_current, False),
                ("quant", "percent", tr("quant"), self.show_quant, False),
                ("export", "export", tr("export_all").rstrip("…."), self.export, False)):
            b = QToolButton(); b.setText(text.rstrip("…."))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setIcon(icon(ic, "#FFFFFF" if primary else None)); b.setIconSize(QSize(17, 17))
            if primary:
                b.setObjectName("primaryTool")
            b.clicked.connect(slot)
            tl.addWidget(b)
            self.tool[key] = b
        tl.addStretch(1)
        pl = QLabel(); pl.setPixmap(icon("palette", C["muted"]).pixmap(17, 17)); tl.addWidget(pl)
        self.palette = PalettePicker()
        self.palette.changed.connect(self.set_theme)
        tl.addWidget(self.palette)
        ab = QToolButton(); ab.setIcon(icon("bot")); ab.setText(tr("agent"))
        ab.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        ab.clicked.connect(lambda: AgentDialog(self.project, self).exec())
        tl.addWidget(ab)
        outer.addWidget(top)

        # ---- body: sidebar | (plot / results) | inspector
        body = QWidget()
        bl = QHBoxLayout(body); bl.setContentsMargins(10, 10, 10, 6); bl.setSpacing(0)
        split = QSplitter(Qt.Orientation.Horizontal); split.setChildrenCollapsible(False)
        bl.addWidget(split)
        outer.addWidget(body, 1)

        # sidebar
        side, sl = _card(tr("samples"))
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(2)
        self.tree.setIndentation(14)
        self.tree.header().setStretchLastSection(False)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.currentItemChanged.connect(self._tree_changed)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._tree_menu)
        sl.addWidget(self.tree)
        side.setMinimumWidth(240)
        split.addWidget(side)

        # centre: plot card + results card
        vsplit = QSplitter(Qt.Orientation.Vertical); vsplit.setChildrenCollapsible(False)
        plot_card, pl_ = _card(None)
        hdr = QHBoxLayout(); hdr.setContentsMargins(4, 0, 0, 0)
        self.plot_title = QLabel(""); self.plot_title.setObjectName("cardTitle")
        self.plot_sub = QLabel(""); self.plot_sub.setObjectName("hint")
        hdr.addWidget(self.plot_title); hdr.addSpacing(8); hdr.addWidget(self.plot_sub); hdr.addStretch(1)
        self.view = SpectrumView()
        btns = {}
        for ic, tip, chk in (("home", tr("view_reset"), False), ("move", tr("view_pan"), True),
                             ("zoom", tr("view_zoom"), True), ("image", tr("view_save"), False)):
            b = QToolButton(); b.setIcon(icon(ic, C["muted"])); b.setToolTip(tip); b.setCheckable(chk)
            b.setIconSize(QSize(16, 16))
            hdr.addWidget(b)
            btns[ic] = b
        btns["home"].clicked.connect(self.view.view_home)
        btns["image"].clicked.connect(self.view.view_save)
        btns["move"].toggled.connect(self.view.view_pan)
        btns["zoom"].toggled.connect(self.view.view_zoom)
        btns["move"].toggled.connect(lambda on: on and btns["zoom"].setChecked(False))
        btns["zoom"].toggled.connect(lambda on: on and btns["move"].setChecked(False))
        pl_.addLayout(hdr)
        pl_.addWidget(self.view, 1)
        self.view.edited.connect(self._canvas_edited)
        self.view.add_peak.connect(self._add_peak_at)
        self.view.remove_comp.connect(self._remove_comp)
        self.view.status.connect(lambda s: self.statusBar().showMessage(s, 3000))
        vsplit.addWidget(plot_card)

        res_card, rl = _card(None, margins=(6, 2, 6, 6))
        self.tabs = QTabWidget(); self.tabs.setDocumentMode(True)
        self.res_tab = QTableWidget(); self.res_tab.verticalHeader().setVisible(False)
        self.res_tab.setShowGrid(False); self.res_tab.setAlternatingRowColors(True)
        self.res_tab.horizontalHeader().setStretchLastSection(True)
        self.diag_txt = QPlainTextEdit(); self.diag_txt.setReadOnly(True)
        self.quant_tab = QTableWidget(); self.quant_tab.verticalHeader().setVisible(False)
        self.quant_tab.setShowGrid(False)
        self.quant_tab.itemChanged.connect(self._rsf_edited)
        self.log = QPlainTextEdit(); self.log.setReadOnly(True)
        self.tabs.addTab(self.res_tab, tr("results"))
        self.tabs.addTab(self.diag_txt, tr("diagnose"))
        self.tabs.addTab(self.quant_tab, tr("quant"))
        self.tabs.addTab(self.log, tr("log"))
        rl.addWidget(self.tabs)
        vsplit.addWidget(res_card)
        vsplit.setStretchFactor(0, 5); vsplit.setStretchFactor(1, 2)
        vsplit.setSizes([620, 230])
        split.addWidget(vsplit)

        # inspector
        insp, il = _card(tr("inspector"), margins=(0, 12, 0, 0))
        self.panel.changed.connect(self._panel_changed)
        self.panel.fit_requested.connect(self.fit_current)
        self.panel.diag_requested.connect(self.diagnose_current)
        self.panel.preset_requested.connect(self._preset_requested)
        sa = QScrollArea(); sa.setWidgetResizable(True); sa.setWidget(self.panel)
        sa.setFrameShape(QFrame.Shape.NoFrame)
        self.panel.setObjectName("modelPanel")
        sa.viewport().setObjectName("modelPanel")
        il.addWidget(sa)
        insp.setMinimumWidth(480)
        split.addWidget(insp)
        split.setStretchFactor(0, 0); split.setStretchFactor(1, 1); split.setStretchFactor(2, 0)
        split.setSizes([250, 880, 500])

        self.metric_lbl = QLabel(""); self.metric_lbl.setObjectName("metric")
        self.statusBar().addPermanentWidget(self.metric_lbl)
        cr = QLabel(f"{CREDIT}   ·   {tr('disclaimer_short')}  "); cr.setObjectName("hint")
        cr.setToolTip(DISCLAIMER_ZH if i18n.lang() == "zh" else DISCLAIMER_EN)
        self.statusBar().addPermanentWidget(cr)

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
        self._act(m, tr("import_mapped"), self.import_mapped)
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
        m = mb.addMenu(tr("menu_agent"))
        self._act(m, tr("agent_connect"), lambda: AgentDialog(self.project, self).exec())
        m = mb.addMenu(tr("menu_help"))
        self._act(m, tr("disclaimer"), lambda: self.show_disclaimer(True))
        self._act(m, tr("validate"), self.validate_project)
        self._act(m, tr("diag_zip"), self.export_diagnostics)
        self._act(m, tr("open_log"), self.open_log_folder)
        self._act(m, tr("about"), self.about)


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
        log.warning("GUI error: %s", msg)
        box = QMessageBox(QMessageBox.Icon.Warning, APP_NAME, msg.splitlines()[0][:500], parent=self)
        if len(msg.splitlines()) > 1 or len(msg) > 500:
            box.setDetailedText(msg)
        box.exec()

    @staticmethod
    def err(e: Exception) -> str:
        """Message of an exception in the UI language (ReadError carries zh / en)."""
        return e.text(i18n.lang()) if isinstance(e, ReadError) else str(e)

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
        except (OSError, ValueError) as e:      # SchemaError / ReadError are ValueErrors
            self.fail(f"{path}\n{self.err(e)}")
            return
        self._remember(self.project.path)
        self.setWindowTitle(f"{APP_NAME} — {self.project.name}")
        th = theme_id(self.project.settings.get("theme"))
        self.view.theme = th
        self.palette.set_theme(th)
        self.brand_sub.setText(f"·   {self.project.name}")
        self._watch()
        self.refresh_tree()
        self.log.appendPlainText(time.strftime("%H:%M:%S  ") + self.project.path)
        self.statusBar().showMessage(f"{self.project.name}: {len(self.project.spectra)} spectra", 4000)

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
        except (OSError, ValueError) as e:      # half-written file from the agent: retry on next change
            log.warning("external reload of %s failed: %s", self.project.path, e)
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
        self._add_files(files)

    def _add_files(self, files, template: str | None = None):
        self._mark_write()
        failed_tables = []
        for f in files:
            try:
                keys = self.project.add_file(f, template=template)
                self.say(f"+ {os.path.basename(f)}: {len(keys)} spectra")
            except (OSError, ValueError) as e:
                if template is None and os.path.splitext(f)[1].lower() in TableReader.suffixes:
                    failed_tables.append(f)
                self.fail(f"{f}: {self.err(e)}")
        self.refresh_tree()
        if failed_tables:
            self.import_mapped(failed_tables)

    def import_mapped(self, files=None):
        """Import tables through a saved column template or a new one made in the wizard."""
        if self.project is None:
            self.new_project()
            if self.project is None:
                return
        if not files:
            files, _ = QFileDialog.getOpenFileNames(self, tr("import_mapped"), "",
                                                    "Tables (*.csv *.txt *.dat *.xy *.xlsx *.xls *.xlsm);;All files (*)")
            if not files:
                return
        new = tr("wiz_title") + "…"
        names = list(self.project.formats)
        name = new
        if names:
            name, ok = QInputDialog.getItem(self, tr("template"), tr("template"), [new] + names, 0, False)
            if not ok:
                return
        if name == new:
            from .colwizard import ColumnWizard
            try:
                dlg = ColumnWizard(files[0], self.project.formats, self)
            except (OSError, ValueError) as e:
                self.fail(f"{files[0]}: {self.err(e)}")
                return
            if not dlg.exec():
                return
            try:
                self._mark_write()
                self.project.add_template(dlg.template_name, dlg.template)
            except ValueError as e:
                self.fail(self.err(e))
                return
            name = dlg.template_name
        self._add_files(files, template=name)

    # ------------------------------------------------------------------ help: validation / diagnostics
    def validate_project(self):
        if self.project is None:
            self.fail(tr("no_project"))
            return
        from .. import schema
        rep = schema.validate_project(self.project.path)
        if not rep.items:
            QMessageBox.information(self, APP_NAME, tr("validate_ok"))
            return
        self.say(rep.text())
        box = QMessageBox(QMessageBox.Icon.Warning if rep.n_err else QMessageBox.Icon.Information, APP_NAME,
                          tr("validate_title", e=rep.n_err, w=rep.n_warn), parent=self)
        box.setDetailedText(rep.text())
        box.exec()

    def export_diagnostics(self):
        from .. import logs
        try:
            path = logs.diagnostics_zip(project=self.project)
        except OSError as e:
            self.fail(str(e))
            return
        self.say(f"{tr('diag_done')} {path}")
        QMessageBox.information(self, APP_NAME, f"{tr('diag_done')}\n{path}")
        self.open_log_folder()

    def open_log_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices
        from .. import logs
        logs.LOG_DIR.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(logs.LOG_DIR)))

    # ------------------------------------------------------------------ tree
    def refresh_tree(self, select: str | None = None):
        p = self.project
        self.tree.blockSignals(True)
        self.tree.clear()
        first = None
        target = None
        for smp in p.samples():
            sh = p.shift(smp)
            it = QTreeWidgetItem([p.sample_label(smp), f"{sh:+.2f} eV"])
            f = it.font(0); f.setBold(True); it.setFont(0, f)
            it.setForeground(1, QColor(C["faint"]))
            it.setToolTip(1, tr("shift"))
            it.setData(0, Qt.ItemDataRole.UserRole, ("sample", smp))
            self.tree.addTopLevelItem(it)
            for k in p.keys(sample=smp):
                s = p.spectra[k]
                rec = p.get_model_record(k)
                ch = QTreeWidgetItem(["", ""])
                ch.setData(0, Qt.ItemDataRole.UserRole, ("spec", k))
                self._decorate(ch, s, rec)
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

    def _decorate(self, item, s, rec):
        """Region row: status dot (grey = no model, amber = not fitted / stale, green = fitted) + RMS."""
        item.setText(0, s.region + (f"  #{s.index}" if s.index else ""))
        if rec and rec.get("result") and not rec.get("result_stale"):
            col, rms = C["ok"], f"{rec['result'].get('rms_pct', 0):.2f} %"
        elif rec:
            col, rms = C["warn"], (f"{rec['result'].get('rms_pct', 0):.2f} %" if rec.get("result") else "—")
        else:
            col, rms = "#C9CDD4", ""
        item.setIcon(0, _dot(col))
        item.setText(1, rms)
        item.setForeground(1, QColor(C["muted"]))

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
        if kind == "spec":
            m.addAction(tr("set_region"), lambda: self.assign_region(val))
            m.addSeparator()
        m.addAction(tr("set_shift"), lambda: self.set_shift(smp))
        m.addAction(tr("rename_sample"), lambda: self.rename_sample(smp))
        m.addAction(tr("remove_sample"), lambda: self.remove_sample(smp))
        m.exec(self.tree.viewport().mapToGlobal(pos))

    def assign_region(self, key):
        """Pick the element / core level for a spectrum (any element Li–U, or a single sub-level)."""
        choices = presets.orbital_choices()
        labels = [d for _k, d in choices]
        cur = self.project.spectra[key].region
        idx = next((i for i, (k, _d) in enumerate(choices) if k == cur), 0)
        txt, ok = QInputDialog.getItem(self, tr("set_region"),
                                       "Fe 2p · Fe 2p3/2 · Ce 3d …", labels, idx, True)
        if not ok or not txt.strip():
            return
        region = next((k for k, d in choices if d == txt), txt.strip())
        self._mark_write()
        new = self.project.set_region(key, region)
        self.say(f"{key} → {new}")
        self.refresh_tree(select=new)

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
            except (ValueError, KeyError, FloatingPointError) as e:
                log.warning("evaluate %s: %s", key, e)
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
        t.resizeColumnsToContents()
        approx = "≈" if res.noise == "estimated" else ""
        msg = f"{tr('rms')} {res.rms_pct:.2f} %     χ²ᵣ {approx}{res.chi2_red:.2f}     BIC {res.bic:.1f}"
        if res.bound_hits:
            msg += f"     ⚠ {len(res.bound_hits)} @bounds"
            self.metric_lbl.setToolTip("\n".join(res.bound_hits))
        else:
            self.metric_lbl.setToolTip("")
        self.metric_lbl.setText(msg + "   ")

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
        self._decorate(it, s, rec)

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
                except Exception as e:     # noqa: BLE001 — one failed fit must not stop the batch
                    log.warning("fit %s failed", k, exc_info=True)
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
        for smp, why in self.project.charge_failures.items():
            self.say(f"{tr('charge_failed')} {smp}: {why}")
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
        t.setToolTip(tr("quant_method"))
        t.blockSignals(False)
        self.say(tr("quant_method"))
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
        disc = DISCLAIMER_ZH if i18n.lang() == "zh" else DISCLAIMER_EN
        QMessageBox.about(self, APP_NAME, f"<h2 style='margin-bottom:2px'>{APP_NAME} {__version__}</h2>"
                          f"<p style='color:#2F6BDF;font-weight:600;margin-top:0'>{CREDIT}</p>"
                          "<p>XPS analysis · SPE/VMS/CSV/Excel · constrained peak fitting for all elements "
                          "Li–U · diagnostics · Origin export · MCP agent interface.</p>"
                          f"<p style='color:#6B7280'><b>{tr('disclaimer')}</b><br>{disc}</p>"
                          "<p>MIT License · <a href='https://github.com/Wiolic/PeakForge'>github.com/Wiolic/PeakForge</a></p>")

    def show_disclaimer(self, force: bool = False):
        """Shown once per version on first start (and from Help menu)."""
        key = f"disclaimer_ack_{__version__}"
        if not force and i18n.settings().get(key):
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("disclaimer"))
        box.setIcon(QMessageBox.Icon.Information)
        box.setText(f"<b>{APP_NAME}</b> · {CREDIT}")
        box.setInformativeText(DISCLAIMER_ZH if i18n.lang() == "zh" else DISCLAIMER_EN)
        box.setStandardButtons(QMessageBox.StandardButton.Ok)
        box.button(QMessageBox.StandardButton.Ok).setText(tr("disclaimer_ok"))
        box.exec()
        i18n.save_setting(key, True)
