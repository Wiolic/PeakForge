"""Palette picker (grouped by landscape family, with colour strips) and custom palette editor."""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QStandardItem
from PySide6.QtWidgets import (QColorDialog, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout,
                               QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout)

from ..export import themes as T
from .i18n import lang, tr
from .style import SWATCH_SIZE, swatch

_CUSTOM = "__custom__"


class PalettePicker(QComboBox):
    changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIconSize(SWATCH_SIZE)
        self.setMinimumWidth(260)
        self.setMaxVisibleItems(40)
        self._current = T.DEFAULT
        self.rebuild()
        self.activated.connect(self._activated)

    def rebuild(self, select: str | None = None):
        select = select or self._current
        self.blockSignals(True)
        self.clear()
        model = self.model()
        zh = lang() == "zh"
        for fid, fzh, fen, ids in T.grouped():
            head = QStandardItem(f"{fzh}  {fen}" if zh else f"{fen}  {fzh}")
            head.setFlags(Qt.ItemFlag.NoItemFlags)
            f = head.font(); f.setBold(True); f.setPointSizeF(8.5); head.setFont(f)
            head.setForeground(QColor("#6B7280"))
            model.appendRow(head)
            for tid in ids:
                th = T.THEMES[tid]
                kind = T.KINDS.get(th.get("kind", "poly"), ("", ""))[0 if zh else 1]
                name = f"{th['name_zh']}  {th['name_en']}" if zh else f"{th['name_en']}  {th['name_zh']}"
                self.addItem(swatch(th["components"][:6] + [th["envelope"]]), f"{name}   · {kind}", tid)
        self.insertSeparator(self.count())
        self.addItem(tr("palette_new"), _CUSTOM)
        i = self.findData(T.theme_id(select))
        self.setCurrentIndex(i if i >= 0 else 1)
        self._current = self.currentData()
        self.blockSignals(False)

    def set_theme(self, tid: str):
        self._current = T.theme_id(tid)
        i = self.findData(self._current)
        if i >= 0:
            self.blockSignals(True)
            self.setCurrentIndex(i)
            self.blockSignals(False)

    def _activated(self, i):
        tid = self.itemData(i)
        if tid == _CUSTOM:
            dlg = PaletteEditor(self._current, self)
            if dlg.exec():
                new = dlg.save()
                self.rebuild(new)
                self._current = new
                self.changed.emit(new)
            else:
                self.set_theme(self._current)
            return
        if tid:
            self._current = tid
            self.changed.emit(tid)


class _ColorButton(QPushButton):
    def __init__(self, rgb, parent=None):
        super().__init__(parent)
        self.setFixedSize(34, 24)
        self.set(rgb)
        self.clicked.connect(self._pick)

    def set(self, rgb):
        self.rgb = tuple(rgb)
        self.setStyleSheet(f"background:{T.to_hex(self.rgb)};border:1px solid #D3D6DD;border-radius:6px;")
        self.setToolTip(T.to_hex(self.rgb))

    def _pick(self):
        c = QColorDialog.getColor(QColor(*self.rgb), self)
        if c.isValid():
            self.set((c.red(), c.green(), c.blue()))


class PaletteEditor(QDialog):
    """Start from an existing theme, change colours, save as a custom palette."""

    def __init__(self, base: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("palette_new"))
        th = T.theme(base)
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.name_zh = QLineEdit(th["name_zh"] + "·自定义")
        self.name_en = QLineEdit(th["name_en"] + " custom")
        f.addRow("中文名", self.name_zh)
        f.addRow("English name", self.name_en)
        lay.addLayout(f)
        g = QGridLayout()
        self.data = _ColorButton(th["data"]); self.bg = _ColorButton(th["background"])
        self.env = _ColorButton(th["envelope"])
        for col, (lab, w) in enumerate((("Measured", self.data), ("Background", self.bg), ("Envelope", self.env))):
            g.addWidget(QLabel(lab), 0, col); g.addWidget(w, 1, col)
        lay.addLayout(g)
        lay.addWidget(QLabel(tr("components")))
        g2 = QGridLayout()
        self.comps = []
        for i in range(8):
            b = _ColorButton(th["components"][i % len(th["components"])])
            self.comps.append(b)
            g2.addWidget(QLabel(str(i + 1)), 0, i, alignment=Qt.AlignmentFlag.AlignCenter)
            g2.addWidget(b, 1, i)
        lay.addLayout(g2)
        r = QHBoxLayout()
        self.alpha = QDoubleSpinBox(); self.alpha.setRange(0.05, 1.0); self.alpha.setSingleStep(0.05)
        self.alpha.setValue(th["fill_alpha"])
        r.addWidget(QLabel(tr("fill_alpha"))); r.addWidget(self.alpha); r.addStretch(1)
        lay.addLayout(r)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def save(self) -> str:
        spec = dict(data=self.data.rgb, background=self.bg.rgb, envelope=self.env.rgb,
                    components=[b.rgb for b in self.comps], fill_alpha=self.alpha.value())
        tid = self.name_en.text().strip().lower().replace(" ", "_") or "custom"
        return T.save_user_theme(tid, self.name_zh.text().strip(), self.name_en.text().strip(), spec)
