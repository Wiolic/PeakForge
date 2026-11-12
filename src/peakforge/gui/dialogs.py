"""Dialogs: export, batch apply, agent connection."""
from __future__ import annotations

import json
import os

from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QPlainTextEdit, QPushButton, QSpinBox, QVBoxLayout)
from PySide6.QtCore import Qt

from ..export.origin import originpro_available
from .i18n import tr


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
        from .palette import PalettePicker
        self.theme = PalettePicker()
        self.theme.set_theme(project.palette().get("combo"))
        self.use_project = QCheckBox(tr("export_project_colors"))
        self.use_project.setChecked(True)
        self.theme.setEnabled(False)
        self.use_project.toggled.connect(lambda on: self.theme.setEnabled(not on))
        f.addRow(tr("theme"), self.use_project)
        f.addRow("", self.theme)
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
                    theme=None if self.use_project.isChecked() else self.theme.currentData(), out_dir=self.out.text(), dpi=self.dpi.value())


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
    """Connect an AI agent. Main path for non-programmers: pick the data folder -> PeakForge writes
    .mcp.json + AGENTS.md there -> open that folder in the Claude desktop app's Code tab."""

    def __init__(self, project, parent=None):
        super().__init__(parent)
        from ..agent import config_snippets, connect_folder
        self.setWindowTitle(tr("agent_connect"))
        self.resize(760, 560)
        lay = QVBoxLayout(self)
        lay.setSpacing(10)
        t = QLabel(tr("agent_text")); t.setWordWrap(True)
        lay.addWidget(t)

        step = QLabel(tr("agent_step1")); step.setObjectName("cardTitle"); step.setWordWrap(True)
        lay.addWidget(step)
        row = QHBoxLayout()
        self.folder = QLineEdit(project.root if project is not None else "")
        pick = QPushButton(tr("choose"))
        pick.clicked.connect(lambda: self.folder.setText(
            QFileDialog.getExistingDirectory(self, tr("agent_step1"), self.folder.text()) or self.folder.text()))
        row.addWidget(self.folder, 1); row.addWidget(pick)
        lay.addLayout(row)
        go = QPushButton(tr("agent_connect_btn")); go.setObjectName("primary")
        self.result = QLabel(""); self.result.setWordWrap(True); self.result.setObjectName("hint")
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        def do_connect():
            f = self.folder.text().strip()
            if not f:
                return
            out = connect_folder(f)
            self.result.setText(f"✓ {out['mcp_json']}\n✓ {out['agents_md']}\n\n{tr('agent_step2')}")
        go.clicked.connect(do_connect)
        lay.addWidget(go)
        lay.addWidget(self.result)

        adv = QLabel(tr("agent_advanced")); adv.setObjectName("sectionTitle")
        lay.addWidget(adv)
        cfg = config_snippets()
        for title, text in (("Claude Code (terminal)", cfg["claude_code_cli"]),
                            (".mcp.json / Cursor / Claude Desktop", json.dumps(cfg["mcp_json"], indent=2)),
                            ("Codex (~/.codex/config.toml)", cfg["codex_toml"])):
            r2 = QHBoxLayout()
            lab = QLabel(f"<b>{title}</b>")
            b = QPushButton(tr("copy")); b.setObjectName("ghost")
            b.clicked.connect(lambda _=False, s=text: QGuiApplication.clipboard().setText(s))
            r2.addWidget(lab); r2.addStretch(1); r2.addWidget(b)
            lay.addLayout(r2)
            box = QPlainTextEdit(text); box.setReadOnly(True); box.setMaximumHeight(70)
            lay.addWidget(box)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        lay.addWidget(bb)
