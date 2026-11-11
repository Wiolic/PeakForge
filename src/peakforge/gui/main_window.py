"""PeakForge main window."""
from __future__ import annotations

import os
import time

from PySide6.QtCore import QFileSystemWatcher, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon, QKeySequence
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QHeaderView, QLabel, QMainWindow, QMessageBox, QPlainTextEdit,
                               QScrollArea, QSplitter, QTableWidget, QTabWidget, QToolButton, QTreeWidget,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, CREDIT, DISCLAIMER_EN, DISCLAIMER_ZH, __version__
from ..io import ReadError
from ..logs import log
from ..project import Project
from ..core.model import RegionModel
from . import i18n
from .canvas import SpectrumView
from .dialogs import AgentDialog
from .i18n import tr
from .model_panel import ModelPanel
from .palette import PalettePicker
from .style import C, icon
from .window.charge_quant import ChargeQuantMixin
from .window.common import ICON, _card, _dot  # noqa: F401  (re-exported)
from .window.editing import EditMixin
from .window.jobs import JobsMixin
from .window.project_io import ProjectMixin
from .window.tree import TreeMixin


class MainWindow(ProjectMixin, TreeMixin, EditMixin, JobsMixin, ChargeQuantMixin, QMainWindow):
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
