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
                self.addItem(swatch(T.preview_colors(tid)), T.display_name(tid, "zh" if zh else "en"), tid)
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


class FigureColorDialog(QDialog):
    """Base colour (swatch grid) and component colour mode of ONE figure, with a live preview."""

    def __init__(self, project, key: str, n: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("figure_colors"))
        pal = project.palette()
        fig = (pal.get("figures") or {}).get(key, {})
        s = project.spectra[key]
        regs = [x.region for x in project.spectra.values() if not x.is_survey]
        self._auto = T.resolve_base(pal, s.region, regs)
        self.base: str | None = fig.get("base") if fig.get("base") in T.BASE_COLORS else None
        self._n = max(2, n)
        zh = lang() == "zh"
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(f"{project.sample_label(s.sample)} · {s.region}"))
        lay.addWidget(QLabel(tr("color_base")))
        grid = QGridLayout()
        self._btns: dict[str | None, QPushButton] = {}
        nm = "name_zh" if zh else "name_en"
        items = [(None, tr("color_auto") + f" ({T.BASE_COLORS[self._auto][nm]})", T.BASE_COLORS[self._auto]["hex"])]
        items += [(b, v[nm], v["hex"]) for b, v in T.BASE_COLORS.items()]
        for i, (b, name, hx) in enumerate(items):
            btn = QPushButton("A" if b is None else "")
            btn.setCheckable(True)
            btn.setFixedSize(54, 28)
            btn.setToolTip(name)
            btn.setStyleSheet(f"QPushButton{{background:{hx};border:1px solid #D3D6DD;border-radius:6px;color:white;}}"
                              "QPushButton:checked{border:3px solid #111827;}")
            btn.clicked.connect(lambda _=False, bb=b: self._pick(bb))
            self._btns[b] = btn
            grid.addWidget(btn, i // 7, i % 7)
        lay.addLayout(grid)
        lay.addWidget(QLabel(tr("color_mode")))
        self.mode = QComboBox()
        self.mode.addItem(tr("mode_series"), "series")
        self.mode.addItem(tr("mode_gradient"), "gradient")
        self.mode.setCurrentIndex(1 if (fig.get("mode") or pal.get("mode")) == "gradient" else 0)
        self.mode.currentIndexChanged.connect(self._update)
        lay.addWidget(self.mode)
        lay.addWidget(QLabel(tr("color_preview")))
        self.preview = QLabel()
        lay.addWidget(self.preview)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        rst = bb.addButton(tr("color_reset"), QDialogButtonBox.ButtonRole.ResetRole)
        rst.clicked.connect(lambda: (self._pick(None), self.mode.setCurrentIndex(0)))
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
        self._pick(self.base)

    def _pick(self, base):
        self.base = base
        for b, btn in self._btns.items():
            btn.setChecked(b == base)
        self._update()

    def _update(self):
        cols = T.series(self.base or self._auto, self._n, self.mode.currentData())
        self.preview.setPixmap(swatch(cols, 300, 22).pixmap(600, 44))

    def values(self) -> dict:
        mode = self.mode.currentData()
        return dict(base=self.base, mode=None if mode == "series" else mode)
