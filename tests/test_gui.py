"""GUI smoke test (offscreen): every module imports, the main window and all dialogs build,
a project opens, a spectrum is fitted and exported from the window's code paths."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("PySide6")


@pytest.fixture(scope="module")
def app():
    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtWidgets import QApplication
    from peakforge.gui.style import QSS, mpl_style
    a = QApplication.instance() or QApplication([])
    a.setStyleSheet(QSS)
    mpl_style()
    return a


def test_all_gui_modules_import():
    import importlib
    for m in ("app", "canvas", "dialogs", "i18n", "main_window", "model_panel", "palette", "style", "workers"):
        importlib.import_module(f"peakforge.gui.{m}")


def test_window_project_fit_and_dialogs(app, tmp_path):
    from PySide6.QtCore import QThreadPool
    from peakforge.gui.dialogs import AgentDialog, BatchDialog, ExportDialog
    from peakforge.gui.main_window import MainWindow
    from peakforge.gui.palette import PaletteEditor
    from peakforge.project import Project
    ex = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_fresh.csv")
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_file(ex)
    w = MainWindow(p.path)
    key = w.project.keys("O 1s")[0]
    w.select_key(key)
    w._preset_requested("")
    w.fit_current(1)
    QThreadPool.globalInstance().waitForDone(60000)
    for _ in range(5):
        app.processEvents()
    assert w.model is not None and w.project.get_model_record(key).get("result")
    for d in (AgentDialog(w.project, w), BatchDialog(w.project, key, w), ExportDialog(w.project, w),
              PaletteEditor("glacier", w)):
        d.close()
    from peakforge.agent import connect_folder
    out = connect_folder(str(tmp_path / "data"))
    assert os.path.exists(out["mcp_json"]) and os.path.exists(out["agents_md"])
    w.close()
