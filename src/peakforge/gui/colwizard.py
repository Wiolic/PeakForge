"""Column-mapping wizard for CSV / TXT / Excel files (back end: io/wizard.py).

The user picks the energy column, the intensity columns, BE or KE, cps or counts (+ time per point)
and the region of each column; "Try" reads the file with that mapping and the result is saved as a
named column template in the project ("formats"), so later files with the same layout import
with one click.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QPlainTextEdit, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)

from ..io import ReadError
from ..io.wizard import build_template, inspect_table, try_read
from ..spectrum import element_of, normalize_region
from . import i18n
from .i18n import tr


def err_text(e: Exception) -> str:
    return e.text(i18n.lang()) if isinstance(e, ReadError) else str(e)


class ColumnWizard(QDialog):
    def __init__(self, path: str, existing: dict | None = None, parent=None):
        super().__init__(parent)
        self.path = path
        self.template: dict | None = None
        self.setWindowTitle(tr("wiz_title"))
        self.resize(900, 620)
        self.info = inspect_table(path)          # raises ReadError → caller shows it
        lay = QVBoxLayout(self)
        hint = QLabel(tr("wiz_hint")); hint.setWordWrap(True)
        lay.addWidget(hint)
        f = QFormLayout()
        self.sheet = QComboBox()
        for s in self.info:
            self.sheet.addItem(s["sheet"])
        self.sheet.currentIndexChanged.connect(self._fill)
        if len(self.info) > 1:
            f.addRow(tr("wiz_sheet"), self.sheet)
        self.x = QComboBox()
        f.addRow(tr("wiz_x"), self.x)
        row = QHBoxLayout()
        self.energy = QComboBox()
        self.energy.addItem(tr("wiz_be"), "binding"); self.energy.addItem(tr("wiz_ke"), "kinetic")
        self.hv = QDoubleSpinBox(); self.hv.setRange(10, 20000); self.hv.setDecimals(2); self.hv.setValue(1486.6)
        self.hv.setSuffix(" eV")
        row.addWidget(self.energy); row.addWidget(QLabel("hν")); row.addWidget(self.hv); row.addStretch(1)
        f.addRow(tr("wiz_energy"), row)
        row2 = QHBoxLayout()
        self.intensity = QComboBox()
        self.intensity.addItem(tr("wiz_cps"), "cps"); self.intensity.addItem(tr("wiz_counts"), "counts")
        self.use_t = QCheckBox(tr("wiz_time"))
        self.t = QDoubleSpinBox(); self.t.setRange(1e-4, 1e5); self.t.setDecimals(4); self.t.setValue(1.0)
        self.t.setSuffix(" s")
        row2.addWidget(self.intensity); row2.addWidget(self.use_t); row2.addWidget(self.t); row2.addStretch(1)
        f.addRow(tr("wiz_intensity"), row2)
        lay.addLayout(f)
        lay.addWidget(QLabel(tr("wiz_cols")))
        self.table = QTableWidget()
        self.table.verticalHeader().setVisible(False)
        lay.addWidget(self.table, 1)
        self.out = QPlainTextEdit(); self.out.setReadOnly(True); self.out.setMaximumHeight(110)
        lay.addWidget(self.out)
        nrow = QHBoxLayout()
        self.name = QLineEdit(); self.name.setPlaceholderText(tr("wiz_name_ph"))
        nrow.addWidget(QLabel(tr("wiz_name"))); nrow.addWidget(self.name, 1)
        lay.addLayout(nrow)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.try_btn = bb.addButton(tr("wiz_try"), QDialogButtonBox.ButtonRole.ActionRole)
        self.try_btn.clicked.connect(self._try)
        bb.button(QDialogButtonBox.StandardButton.Ok).setText(tr("ok"))
        bb.button(QDialogButtonBox.StandardButton.Cancel).setText(tr("cancel"))
        bb.accepted.connect(self._accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self.existing = existing or {}
        self.energy.currentIndexChanged.connect(self._sync)
        self.intensity.currentIndexChanged.connect(self._sync)
        self.use_t.toggled.connect(self._sync)
        self.x.currentIndexChanged.connect(self._x_changed)
        self._fill()

    # ---------------------------------------------------------------- table
    def _cur(self) -> dict:
        return self.info[max(self.sheet.currentIndex(), 0)]

    def _label(self, i: int, names: list[str]) -> str:
        return f"{i}: {names[i]}" if names[i] else f"{i}"

    def _fill(self):
        s = self._cur()
        g = s["guess"]
        names = s["names"]
        self.x.blockSignals(True)
        self.x.clear()
        for i in range(s["ncols"]):
            self.x.addItem(self._label(i, names), i)
        self.x.setCurrentIndex(g["x"])
        self.x.blockSignals(False)
        self.energy.setCurrentIndex(0 if g["energy"] == "binding" else 1)
        self.intensity.setCurrentIndex(0 if g["intensity"] == "cps" else 1)
        n = s["ncols"]
        rows = s["rows"]
        self.table.clear()
        self.table.setColumnCount(n)
        self.table.setRowCount(2 + len(rows))
        self.table.setHorizontalHeaderLabels([self._label(i, names) for i in range(n)])
        self.checks, self.regions = [], []
        for c in range(n):
            cb = QCheckBox(tr("wiz_use")); cb.setChecked(c in g["y"])
            self.table.setCellWidget(0, c, cb); self.checks.append(cb)
            head = normalize_region(names[c].split(" / ")[0]) if names[c] else ""
            le = QLineEdit(head if element_of(head) else "")       # prefill only real core levels
            le.setPlaceholderText(tr("wiz_region_ph"))
            self.table.setCellWidget(1, c, le); self.regions.append(le)
            for r, vals in enumerate(rows):
                v = vals[c] if c < len(vals) else None
                it = QTableWidgetItem("" if v is None else f"{v:g}")
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(2 + r, c, it)
        self.table.setVerticalHeaderLabels([tr("wiz_use"), tr("region")] + [""] * len(rows))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self._x_changed()
        self._sync()

    def _x_changed(self):
        x = self.x.currentData()
        for c, cb in enumerate(self.checks):
            cb.setEnabled(c != x)
            if c == x:
                cb.setChecked(False)
            self.regions[c].setEnabled(c != x)

    def _sync(self):
        self.hv.setEnabled(self.energy.currentData() == "kinetic")
        counts = self.intensity.currentData() == "counts"
        self.t.setEnabled(self.use_t.isChecked())
        self.use_t.setText(tr("wiz_time_counts") if counts else tr("wiz_time"))

    # ---------------------------------------------------------------- template
    def _template(self) -> dict:
        s = self._cur()
        ys = [c for c, cb in enumerate(self.checks) if cb.isChecked()]
        regions = {c: self.regions[c].text().strip() for c in ys if self.regions[c].text().strip()}
        return build_template(s["names"], self.x.currentData(), ys, energy=self.energy.currentData(),
                              hv=self.hv.value(), intensity=self.intensity.currentData(),
                              acq_time=self.t.value() if self.use_t.isChecked() else None,
                              regions=regions, sheet=s["sheet"] if len(self.info) > 1 else None)

    def _try(self) -> bool:
        try:
            tpl = self._template()
            res = try_read(self.path, tpl)
        except (ReadError, ValueError) as e:
            self.out.setPlainText("✗ " + err_text(e))
            return False
        lines = [f"✓ {r['region']}: {r['npts']} {tr('wiz_pts')}, BE {r['be_min']:.2f}–{r['be_max']:.2f} eV, "
                 f"I {r['y_min']:.4g}–{r['y_max']:.4g}"
                 + (f", t = {r['acq_time']:g} s" if r["acq_time"] else "") for r in res]
        self.out.setPlainText("\n".join(lines))
        self.template = tpl
        return True

    def _accept(self):
        if not self._try():
            return
        name = self.name.text().strip()
        if not name:
            self.out.appendPlainText("✗ " + tr("wiz_need_name"))
            return
        self.template_name = name
        self.accept()
