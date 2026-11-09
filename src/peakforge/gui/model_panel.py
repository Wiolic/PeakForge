"""Right-hand panel: preset, background, components and parameter tables, fit controls."""
from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox,
                               QHBoxLayout, QHeaderView, QLabel, QPushButton, QSpinBox,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from .. import presets as presets_mod
from ..core import background as bgmod
from ..core import lineshapes
from ..core.model import RegionModel
from .i18n import lang, tr
from .style import icon


def _fmt(v):
    if v is None or (isinstance(v, float) and not math.isfinite(v)):
        return ""
    return f"{v:.5g}"


def _num(text: str, default):
    t = text.strip()
    if t == "":
        return default
    try:
        return float(t)
    except ValueError:
        return None


class ModelPanel(QWidget):
    changed = Signal()                  # model edited (save + re-evaluate)
    fit_requested = Signal(int)         # n_starts
    diag_requested = Signal()
    preset_requested = Signal(str)      # preset id ('' = automatic)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model: RegionModel | None = None
        self.region = ""
        self.project_dir = None
        self._busy = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 10, 14, 12)
        lay.setSpacing(8)

        # preset
        row = QHBoxLayout()
        self.preset = QComboBox()
        self.btn_apply = QPushButton(tr("apply"))
        self.btn_apply.clicked.connect(lambda: self.preset_requested.emit(self.preset.currentData() or ""))
        row.addWidget(QLabel(tr("preset")))
        row.addWidget(self.preset, 1)
        row.addWidget(self.btn_apply)
        lay.addLayout(row)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName("hint")
        lay.addWidget(self.note)

        # background
        gb = QGroupBox(tr("background"))
        f = QFormLayout(gb)
        self.bg_kind = QComboBox()
        for k in bgmod.KINDS:
            self.bg_kind.addItem(k, k)
        self.bg_lo, self.bg_hi = self._spin(), self._spin()
        self.fr_lo, self.fr_hi = self._spin(), self._spin()
        self.weight = QComboBox()
        self.weight.addItem("none", "none")
        self.weight.addItem("poisson", "poisson")
        f.addRow(tr("bg_kind"), self.bg_kind)
        r2 = QHBoxLayout(); r2.addWidget(self.bg_lo); r2.addWidget(self.bg_hi)
        f.addRow(tr("bg_lo") + " / " + tr("bg_hi"), r2)
        r3 = QHBoxLayout(); r3.addWidget(self.fr_lo); r3.addWidget(self.fr_hi)
        f.addRow(tr("fit_range"), r3)
        f.addRow(tr("weighting"), self.weight)
        for w in (self.bg_kind, self.weight):
            w.currentIndexChanged.connect(self._bg_changed)
        for w in (self.bg_lo, self.bg_hi, self.fr_lo, self.fr_hi):
            w.editingFinished.connect(self._bg_changed)
        lay.addWidget(gb)

        # components
        gc = QGroupBox(tr("components"))
        vc = QVBoxLayout(gc)
        self.comp_tab = QTableWidget(0, 5)
        self.comp_tab.setHorizontalHeaderLabels([tr("col_name"), tr("col_label"), tr("col_shape"),
                                                 tr("col_doublet"), tr("col_total")])
        ch = self.comp_tab.horizontalHeader()
        ch.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (3, 4):
            ch.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.comp_tab.verticalHeader().setVisible(False)
        self.comp_tab.setShowGrid(False)
        self.comp_tab.setMinimumHeight(150)
        self.comp_tab.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.comp_tab.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.comp_tab.itemSelectionChanged.connect(self._fill_params)
        self.comp_tab.itemChanged.connect(self._comp_item_changed)
        vc.addWidget(self.comp_tab)
        rb = QHBoxLayout()
        self.btn_add = QPushButton(icon("plus"), tr("add"))
        self.btn_del = QPushButton(icon("trash"), tr("remove"))
        self.btn_add.setObjectName("ghost"); self.btn_del.setObjectName("ghost")
        rb.addWidget(self.btn_add); rb.addWidget(self.btn_del); rb.addStretch(1)
        vc.addLayout(rb)
        self.btn_add.clicked.connect(self._add_comp)
        self.btn_del.clicked.connect(self._del_comp)
        lay.addWidget(gc, 2)

        # parameters
        gp = QGroupBox(tr("parameters"))
        vp = QVBoxLayout(gp)
        self.par_tab = QTableWidget(0, 7)
        self.par_tab.setHorizontalHeaderLabels([tr("col_param"), tr("col_value"), tr("col_min"), tr("col_max"),
                                                tr("col_vary"), tr("col_expr"), tr("col_err")])
        hh = self.par_tab.horizontalHeader()
        hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        for col in (0, 4, 6):
            hh.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        self.par_tab.verticalHeader().setVisible(False)
        self.par_tab.setShowGrid(False)
        self.par_tab.setAlternatingRowColors(True)
        self.par_tab.setMinimumHeight(200)
        self.par_tab.itemChanged.connect(self._par_item_changed)
        vp.addWidget(self.par_tab)
        lay.addWidget(gp, 3)

        # fit controls
        rf = QHBoxLayout()
        self.starts = QSpinBox(); self.starts.setRange(1, 50); self.starts.setValue(3)
        self.btn_fit = QPushButton(tr("fit"))
        self.btn_fit.setObjectName("primary")
        self.btn_fit.setIcon(icon("play", "#FFFFFF"))
        self.btn_diag = QPushButton(icon("pulse"), tr("diagnose"))
        rf.addWidget(QLabel(tr("starts"))); rf.addWidget(self.starts)
        rf.addStretch(1); rf.addWidget(self.btn_diag); rf.addWidget(self.btn_fit)
        self.btn_fit.clicked.connect(lambda: self.fit_requested.emit(self.starts.value()))
        self.btn_diag.clicked.connect(self.diag_requested.emit)
        lay.addLayout(rf)
        self.stderr = {}
        self.set_model(None, "")

    def _spin(self):
        s = QDoubleSpinBox()
        s.setRange(-10, 2000)
        s.setDecimals(2)
        s.setSingleStep(0.1)
        s.setKeyboardTracking(False)
        return s

    # ------------------------------------------------------------------ populate
    def set_presets(self, region: str, project_dir: str | None):
        self.region, self.project_dir = region, project_dir
        self.preset.blockSignals(True)
        self.preset.clear()
        self.preset.addItem("Auto (preset if available, else peak search)" if lang() == "en"
                            else "自动（有预设用预设，否则自动找峰）", "")
        self.preset.addItem("Generic: automatic peak search (any element)" if lang() == "en"
                            else "通用：自动找峰（适用任何元素）", "__generic__")
        for p in presets_mod.presets_for(region, project_dir):
            self.preset.addItem(p.get("name_zh" if lang() == "zh" else "name_en") or p["id"], p["id"])
        self.preset.blockSignals(False)

    def set_model(self, model: RegionModel | None, region: str, stderr: dict | None = None):
        self.model = model
        self.stderr = stderr or {}
        self._busy = True
        try:
            on = model is not None
            for w in (self.bg_kind, self.bg_lo, self.bg_hi, self.fr_lo, self.fr_hi, self.weight, self.comp_tab,
                      self.par_tab, self.btn_del, self.btn_fit, self.btn_diag):
                w.setEnabled(on)
            if model is None:
                self.comp_tab.setRowCount(0)
                self.par_tab.setRowCount(0)
                self.note.setText(tr("no_model"))
                return
            pid = model.preset
            if pid:
                p = presets_mod.list_presets(self.project_dir).get(pid, {})
                self.note.setText(p.get("note_zh" if lang() == "zh" else "note_en", ""))
                i = self.preset.findData(pid)
                if i >= 0:
                    self.preset.setCurrentIndex(i)
            else:
                self.note.setText("")
            b = model.background
            self.bg_kind.setCurrentIndex(max(0, self.bg_kind.findData(b.kind)))
            fr = model.fit_range or (0, 0)
            self.fr_lo.setValue(min(fr)); self.fr_hi.setValue(max(fr))
            self.bg_lo.setValue(b.lo if b.lo is not None else min(fr))
            self.bg_hi.setValue(b.hi if b.hi is not None else max(fr))
            self.weight.setCurrentIndex(max(0, self.weight.findData(model.weighting)))
            sel = self._selected_name()
            self.comp_tab.setRowCount(len(model.components))
            for i, c in enumerate(model.components):
                it = QTableWidgetItem(c.name); it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.comp_tab.setItem(i, 0, it)
                self.comp_tab.setItem(i, 1, QTableWidgetItem(c.label))
                cb = QComboBox()
                for k, d in lineshapes.SHAPES.items():
                    cb.addItem(k, k)
                cb.setCurrentIndex(cb.findData(c.shape))
                cb.currentIndexChanged.connect(lambda _i, n=c.name, w=cb: self._shape_changed(n, w.currentData()))
                self.comp_tab.setCellWidget(i, 2, cb)
                for col, val in ((3, c.doublet), (4, c.in_total)):
                    chk = QTableWidgetItem()
                    chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    chk.setCheckState(Qt.CheckState.Checked if val else Qt.CheckState.Unchecked)
                    self.comp_tab.setItem(i, col, chk)
            row = next((i for i, c in enumerate(model.components) if c.name == sel), 0)
            if model.components:
                self.comp_tab.selectRow(row)
        finally:
            self._busy = False
        self._fill_params()

    def _selected_name(self):
        r = self.comp_tab.currentRow()
        if r < 0 or self.model is None or r >= len(self.model.components):
            return None
        it = self.comp_tab.item(r, 0)
        return it.text() if it else None

    def _fill_params(self):
        if self._busy and self.par_tab.rowCount():
            pass
        name = self._selected_name()
        self._busy = True
        try:
            if self.model is None or name is None:
                self.par_tab.setRowCount(0)
                return
            c = self.model.comp(name)
            items = list(c.params.items())
            self.par_tab.setRowCount(len(items))
            for i, (k, p) in enumerate(items):
                a = QTableWidgetItem(k); a.setFlags(a.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.par_tab.setItem(i, 0, a)
                self.par_tab.setItem(i, 1, QTableWidgetItem(_fmt(p.value)))
                self.par_tab.setItem(i, 2, QTableWidgetItem(_fmt(p.min)))
                self.par_tab.setItem(i, 3, QTableWidgetItem(_fmt(p.max)))
                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk.setCheckState(Qt.CheckState.Checked if p.vary else Qt.CheckState.Unchecked)
                self.par_tab.setItem(i, 4, chk)
                self.par_tab.setItem(i, 5, QTableWidgetItem(p.expr or ""))
                e = self.stderr.get(f"{name}.{k}")
                ei = QTableWidgetItem(_fmt(e)); ei.setFlags(ei.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.par_tab.setItem(i, 6, ei)
                if p.expr:
                    for col in (1, 2, 3):
                        self.par_tab.item(i, col).setForeground(Qt.GlobalColor.gray)
        finally:
            self._busy = False

    # ------------------------------------------------------------------ edits
    def _bg_changed(self, *_):
        if self._busy or self.model is None:
            return
        m = self.model
        m.background.kind = self.bg_kind.currentData()
        m.background.lo, m.background.hi = self.bg_lo.value(), self.bg_hi.value()
        m.fit_range = (self.fr_lo.value(), self.fr_hi.value())
        m.weighting = self.weight.currentData()
        self.changed.emit()

    def _comp_item_changed(self, it: QTableWidgetItem):
        if self._busy or self.model is None:
            return
        c = self.model.components[it.row()]
        if it.column() == 1:
            c.label = it.text()
        elif it.column() == 3:
            on = it.checkState() == Qt.CheckState.Checked
            orb = presets_mod.orbital(self.model.region) or {}
            c.set_doublet(on, orb.get("split") or 1.0, orb.get("ratio") or 0.5)
            if on:
                c.sub_labels = tuple(orb.get("sub") or ("", ""))
        elif it.column() == 4:
            c.in_total = it.checkState() == Qt.CheckState.Checked
        else:
            return
        self.changed.emit()
        self._fill_params()

    def _shape_changed(self, name, shape):
        if self._busy or self.model is None:
            return
        self.model.comp(name).set_shape(shape)
        self.changed.emit()
        self._fill_params()

    def _par_item_changed(self, it: QTableWidgetItem):
        if self._busy or self.model is None:
            return
        name = self._selected_name()
        if name is None:
            return
        c = self.model.comp(name)
        pn = self.par_tab.item(it.row(), 0).text()
        p = c.params[pn]
        col = it.column()
        if col == 4:
            p.vary = it.checkState() == Qt.CheckState.Checked
        elif col == 5:
            old = p.expr
            p.expr = it.text().strip() or None
            errs = self.model.validate()
            if errs:
                p.expr = old
                it.setText(old or "")
                it.setToolTip("\n".join(errs))
                return
        elif col in (1, 2, 3):
            default = {1: p.value, 2: -math.inf, 3: math.inf}[col]
            v = _num(it.text(), default)
            if v is None:
                return
            if col == 1:
                p.value = v
            elif col == 2:
                p.min = v
            else:
                p.max = v
        self.changed.emit()

    def _add_comp(self):
        if self.model is None:
            return
        self.preset_requested.emit("__add__")

    def _del_comp(self):
        name = self._selected_name()
        if self.model is None or name is None:
            return
        self.model.components = [c for c in self.model.components if c.name != name]
        for _k, c, pn, p in self.model.param_items():
            if p.expr and f"{name}." in p.expr:
                p.expr = None
        self.changed.emit()
        self.set_model(self.model, self.region, self.stderr)
