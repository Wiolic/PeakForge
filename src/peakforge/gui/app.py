"""Application entry: `peakforge gui [project]` or `python -m peakforge`."""
from __future__ import annotations

import os
import sys


def run(project: str | None = None) -> int:
    import matplotlib
    matplotlib.use("QtAgg")
    matplotlib.rcParams["font.family"] = ["Arial", "Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .. import APP_NAME
    from .main_window import ICON, MainWindow

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PeakForge.XPS")
        except Exception:      # noqa: BLE001
            pass
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    if os.path.exists(ICON):
        app.setWindowIcon(QIcon(ICON))
    holder = {}

    def make(path):
        old = holder.get("w")
        w = MainWindow(path, restart_cb=lambda p: make(p))
        if old is not None:
            w.setGeometry(old.geometry())
            old.close()
            old.deleteLater()
        holder["w"] = w
        w.show()

    if project is None and len(sys.argv) > 1 and sys.argv[1].endswith(".xpsproj"):
        project = sys.argv[1]
    make(project)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
