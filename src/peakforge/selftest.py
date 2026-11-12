"""`peakforge selftest`: checks that an installation is complete (used on the packaged app by packaging/smoke.py).

Imports the GUI offscreen, builds the main window and the help window (all pages, both languages), renders the
formulas, checks that every image the documents reference exists and that the package data (presets, orbital table,
Origin template and builder script) are present. Exit code 0 = all fine; problems are printed one per line.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def run() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    problems: list[str] = []
    pkg = Path(__file__).resolve().parent

    for rel in ("data/orbitals.json", "assets/peakforge.ico", "assets/PeakForge_XPS.otpu", "export/origin_builder.py"):
        if not (pkg / rel).exists():
            problems.append(f"missing package file: {rel}")
    from . import presets
    if not presets.list_presets(None):
        problems.append("no built-in presets found")

    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtWidgets import QApplication

    from .gui import help as H
    from .gui import i18n
    from .gui.main_window import MainWindow
    app = QApplication.instance() or QApplication(sys.argv)
    win = MainWindow(None)
    saved = i18n._lang
    try:
        for lang in ("zh", "en"):
            i18n._lang = lang
            hw = H.HelpWindow(win)
            for key in ("gui", "tutorial", "basics", "about"):
                hw.show_tab(key)
                if hw.current_key() != key:
                    problems.append(f"help page {key} ({lang}) not selectable")
            for key, reader in hw.readers.items():
                text = reader.toPlainText()
                if len(text.strip()) < 500:
                    problems.append(f"help page {key} ({lang}) is empty")
                if "$$" in text:
                    problems.append(f"help page {key} ({lang}) has an unrendered formula")
                md = (H.DOCS / H.doc_file(key, lang)).read_text(encoding="utf-8")
                for ref in re.findall(r"!\[[^\]]*\]\(([^)\s]+\.png)\)", md):
                    if not (H.DOCS / ref).exists():
                        problems.append(f"{H.doc_file(key, lang)}: image {ref} missing")
            hw.close()
    finally:
        i18n._lang = saved
    win.close()
    app.processEvents()
    for p in problems:
        print("PROBLEM:", p)
    print("selftest:", "FAILED" if problems else "ok")
    return 1 if problems else 0
