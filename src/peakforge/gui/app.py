"""Application entry: `peakforge gui [project]` or `python -m peakforge`."""
from __future__ import annotations

import os
import sys


def run(project: str | None = None) -> int:
    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication

    from .. import APP_NAME, __version__
    from .main_window import ICON, MainWindow

    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("PeakForge.XPS")
        except Exception:      # noqa: BLE001 — cosmetic (taskbar icon grouping)
            from ..logs import log
            log.debug("AppUserModelID not set", exc_info=True)
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    from .style import QSS, mpl_style
    app.setStyleSheet(QSS)
    mpl_style()
    if os.path.exists(ICON):
        app.setWindowIcon(QIcon(ICON))
    holder = {}
    from .. import logs

    def on_error(text):
        from PySide6.QtWidgets import QMessageBox
        from .i18n import tr
        box = QMessageBox(QMessageBox.Icon.Critical, APP_NAME, tr("unexpected"))
        box.setDetailedText(text)
        box.exec()
    logs.install_excepthook(on_error)
    logs.log.info("GUI %s started", __version__)

    def make(path):
        old = holder.get("w")
        w = MainWindow(path, restart_cb=lambda p: make(p))
        if old is not None:
            w.setGeometry(old.geometry())
            old.close()
            old.deleteLater()
        holder["w"] = w
        w.show()
        if old is None:
            from PySide6.QtCore import QTimer
            QTimer.singleShot(300, w.show_disclaimer)

    if project is None and len(sys.argv) > 1 and sys.argv[1].endswith(".xpsproj"):
        project = sys.argv[1]
    make(project)
    return app.exec()


if __name__ == "__main__":
    sys.exit(run(sys.argv[1] if len(sys.argv) > 1 else None))
