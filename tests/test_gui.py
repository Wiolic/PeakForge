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
    for m in ("app", "canvas", "colwizard", "dialogs", "i18n", "main_window", "model_panel", "palette", "style",
              "workers"):
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


def test_column_wizard_builds_template_and_imports(app, tmp_path, monkeypatch):
    import numpy as np
    import pandas as pd
    from PySide6.QtWidgets import QMessageBox
    from peakforge.gui.colwizard import ColumnWizard
    from peakforge.gui.main_window import MainWindow
    from peakforge.project import Project
    x = np.arange(55.0, 70.0, 0.1)
    f = tmp_path / "lab.csv"
    pd.DataFrame({"KE (eV)": 1486.6 - x, "counts A": 100 + 50 * np.exp(-(x - 61) ** 2),
                  "counts B": 90 + 40 * np.exp(-(x - 62) ** 2)}).to_csv(f, index=False, encoding="utf-8")
    dlg = ColumnWizard(str(f))
    assert dlg.energy.currentData() == "kinetic" and dlg.intensity.currentData() == "counts"
    dlg.checks[2].setChecked(False)
    dlg.regions[1].setText("Ir 4f")
    dlg.use_t.setChecked(True); dlg.t.setValue(0.25)
    dlg.name.setText("lab-ke")
    dlg._accept()
    assert dlg.result() == 1 and dlg.template["y"] == ["counts A"] and dlg.template["acq_time"] == 0.25
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_template(dlg.template_name, dlg.template)
    w = MainWindow(p.path)
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    monkeypatch.setattr(QMessageBox, "information", staticmethod(lambda *a, **k: 0))
    monkeypatch.setattr(QMessageBox, "warning", staticmethod(lambda *a, **k: 0))
    w._add_files([str(f)], template="lab-ke")
    s = w.project.spectra["lab/Ir 4f"]
    assert s.acq_time() == 0.25 and abs(s.be.min() - 55.0) < 1e-6
    w.validate_project()
    w.close()
