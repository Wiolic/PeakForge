"""Dialogs: export, batch apply, agent connection."""
from __future__ import annotations

import json
import os

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout)
from PySide6.QtCore import Qt

from ..export.origin import originpro_available
from ..export.themes import THEMES
from .i18n import lang, tr


class ExportDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("export_title"))
        lay = QVBoxLayout(self)
        f = QFormLayout()
        self.checks = {}
        row = QHBoxLayout()
        for fmt in ("png", "tiff", "svg", "pdf", "xlsx", "origin"):
            c = QCheckBox(fmt.upper() if fmt != "origin" else "Origin (.opju)")
            c.setChecked(fmt in ("png", "xlsx", "origin"))
            self.checks[fmt] = c
            row.addWidget(c)
        f.addRow(tr("formats"), row)
        self.theme = QComboBox()
        for k, t in THEMES.items():
            self.theme.addItem(t["name_zh"] if lang() == "zh" else t["name_en"], k)
        self.theme.setCurrentIndex(max(0, self.theme.findData(project.settings.get("theme", "ir_blue"))))
        f.addRow(tr("theme"), self.theme)
        self.dpi = QSpinBox(); self.dpi.setRange(72, 1200); self.dpi.setValue(300)
        f.addRow("DPI", self.dpi)
        drow = QHBoxLayout()
        self.out = QLineEdit(os.path.join(project.root, "output", "export"))
        b = QPushButton(tr("choose"))
        b.clicked.connect(lambda: self.out.setText(QFileDialog.getExistingDirectory(self, tr("out_dir"), self.out.text()) or self.out.text()))
        drow.addWidget(self.out, 1); drow.addWidget(b)
        f.addRow(tr("out_dir"), drow)
        lay.addLayout(f)
        if not originpro_available():
            lab = QLabel(tr("origin_missing") + " run -pyf build_origin.py")
            lab.setWordWrap(True); lab.setStyleSheet("color:#a60")
            lay.addWidget(lab)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self):
        return dict(formats=tuple(k for k, c in self.checks.items() if c.isChecked()),
                    theme=self.theme.currentData(), out_dir=self.out.text(), dpi=self.dpi.value())


class BatchDialog(QDialog):
    def __init__(self, project, source_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("batch_title"))
        lay = QVBoxLayout(self)
        s = project.spectra[source_key]
        lay.addWidget(QLabel(f"{source_key}  →"))
        gb = QGroupBox(tr("targets")); v = QVBoxLayout(gb)
        self.list = QListWidget()
        for k in project.keys(region=s.region, narrow_only=True):
            if k == source_key:
                continue
            it = QListWidgetItem(k)
            it.setFlags(it.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            it.setCheckState(Qt.CheckState.Checked)
            self.list.addItem(it)
        v.addWidget(self.list); lay.addWidget(gb)
        gf = QGroupBox(tr("fix_params")); h = QHBoxLayout(gf)
        self.fix = {}
        for p in ("fwhm", "eta", "m", "alpha", "gamma", "center"):
            c = QCheckBox(p); c.setChecked(p in ("fwhm", "alpha", "gamma"))
            self.fix[p] = c; h.addWidget(c)
        lay.addWidget(gf)
        self.starts = QSpinBox(); self.starts.setRange(1, 30); self.starts.setValue(3)
        r = QHBoxLayout(); r.addWidget(QLabel(tr("starts"))); r.addWidget(self.starts); r.addStretch(1)
        lay.addLayout(r)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(self.accept); bb.rejected.connect(self.reject)
        lay.addWidget(bb)

    def values(self):
        targets = [self.list.item(i).text() for i in range(self.list.count())
                   if self.list.item(i).checkState() == Qt.CheckState.Checked]
        return dict(targets=targets, fix=tuple(k for k, c in self.fix.items() if c.isChecked()),
                    n_starts=self.starts.value())


class AgentDialog(QDialog):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        from ..agent import config_snippets, write_agents_md
        self.setWindowTitle(tr("agent_connect"))
        self.resize(720, 480)
        lay = QVBoxLayout(self)
        t = QLabel(tr("agent_text")); t.setWordWrap(True)
        lay.addWidget(t)
        cfg = config_snippets()
        for title, text in (("Claude Code", cfg["claude_code_cli"]),
                            (".mcp.json / Cursor / Claude Desktop", json.dumps(cfg["mcp_json"], indent=2)),
                            ("Codex (~/.codex/config.toml)", cfg["codex_toml"])):
            lay.addWidget(QLabel(f"<b>{title}</b>"))
            box = QPlainTextEdit(text); box.setReadOnly(True); box.setMaximumHeight(110)
            lay.addWidget(box)
            b = QPushButton(tr("copy")); b.clicked.connect(lambda _=False, s=text: QGuiApplication.clipboard().setText(s))
            lay.addWidget(b)
        if project is not None:
            lay.addWidget(QLabel(f"PEAKFORGE_PROJECT = {project.path}"))
            b2 = QPushButton(tr("agent_md"))
            b2.clicked.connect(lambda: b2.setText("✓ " + write_agents_md(project.root)))
            lay.addWidget(b2)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
