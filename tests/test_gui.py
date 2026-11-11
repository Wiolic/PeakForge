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
              "tasks"):
        importlib.import_module(f"peakforge.gui.{m}")


def test_window_project_fit_and_dialogs(app, tmp_path):
    from peakforge.gui.tasks import wait_tasks
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
    assert wait_tasks(app, 60)
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


def _window_with_models(app, tmp_path):
    from peakforge.gui.main_window import MainWindow
    from peakforge.project import Project
    ex = os.path.join(os.path.dirname(__file__), "..", "examples")
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_file(os.path.join(ex, "demo_fresh.csv"))
    p.add_file(os.path.join(ex, "demo_aged.csv"))
    keys = p.keys("O 1s")
    assert len(keys) >= 2
    for k in keys:
        p.set_model(k, p.new_model(k))
    w = MainWindow(p.path)
    return w, keys


def _result_of(proj, key):
    rec = proj.get_model_record(key)
    return rec and rec.get("result")


def test_cancelled_fit_all_leaves_project_unchanged(app, tmp_path):
    from peakforge.gui import tasks
    w, keys = _window_with_models(app, tmp_path)
    before = {k: w.project.get_model_record(k) for k in keys}
    w.fit_all()
    assert tasks.active()
    for j in list(tasks._ACTIVE):
        j["handle"].cancel()
    assert tasks.wait_tasks(app, 60)
    assert not tasks.active()
    for k in keys:
        assert w.project.get_model_record(k) == before[k] and not _result_of(w.project, k)
        assert k not in w.project.results
    w.close()


def test_fit_all_and_batch_run_in_background_and_store(app, tmp_path, monkeypatch):
    from peakforge.gui import tasks
    import peakforge.gui.window.jobs as jobs
    w, keys = _window_with_models(app, tmp_path)
    w.fit_all()
    assert tasks.wait_tasks(app, 120)
    assert all(_result_of(w.project, k) for k in keys)
    # batch: copy the model of keys[0] to the other spectra
    for k in keys[1:]:
        w.project.delete_model(k)

    class Dlg:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return True

        def values(self):
            return dict(targets=keys[1:], fix=("fwhm",), n_starts=1)
    monkeypatch.setattr(jobs, "BatchDialog", Dlg)
    w.select_key(keys[0])
    w.batch()
    assert tasks.active()
    assert tasks.wait_tasks(app, 120)
    assert all(_result_of(w.project, k) for k in keys[1:])
    w.close()


def test_result_is_discarded_when_model_changed_during_fit(app, tmp_path):
    from peakforge.gui import tasks
    w, keys = _window_with_models(app, tmp_path)
    key = keys[0]
    w.select_key(key)
    w.fit_current(1)
    assert tasks.active()
    m2 = w.model.copy()
    m2.components[0].params["center"].value += 0.1
    w.project.set_model(key, m2)           # an edit that lands while the fit is running
    assert tasks.wait_tasks(app, 60)
    rec = w.project.get_model_record(key)
    assert rec["model"] == m2.to_json() and not rec.get("result")
    assert key not in w.project.results
    assert f"{key}:" in w.log.toPlainText()     # the user is told (tr() with a key= placeholder)
    w.close()


def test_export_runs_in_background_without_pyplot(app, tmp_path, monkeypatch):
    from peakforge.gui import tasks
    import peakforge.gui.window.jobs as jobs
    w, keys = _window_with_models(app, tmp_path)
    for k in keys:
        w.project.fit(k, n_starts=1)
    out = tmp_path / "exp"

    class Dlg:
        def __init__(self, *a, **k):
            pass

        def exec(self):
            return True

        def values(self):
            return dict(out_dir=str(out), theme="glacier", formats=("png", "xlsx"), dpi=80)
    monkeypatch.setattr(jobs, "ExportDialog", Dlg)
    monkeypatch.setattr(os, "startfile", lambda p: None, raising=False)
    w.export()
    assert tasks.active()
    assert tasks.wait_tasks(app, 120)
    assert list((out / "figures").glob("*.png")) and list(out.glob("*_results.xlsx"))
    w.close()


def test_figures_do_not_use_pyplot():
    import pathlib
    root = pathlib.Path(__file__).parents[1] / "src" / "peakforge"
    for f in list((root / "export").glob("*.py")) + [root / "tasks.py"]:
        txt = f.read_text(encoding="utf-8")
        assert "import matplotlib.pyplot" not in txt and "from matplotlib import pyplot" not in txt, f.name


# ---- phase 3 review regressions
def test_deferred_external_reload_survives_own_write(app, tmp_path):
    """An external change seen while a job runs must still be reloaded after the job's own write."""
    from peakforge.gui import tasks
    w, keys = _window_with_models(app, tmp_path)
    w.fit_all()
    assert tasks.active()
    w._external_reload()                    # agent wrote during the job -> deferred
    assert w._reload_pending
    assert tasks.wait_tasks(app, 120)       # done() wrote: own-write window open
    w._reload_timer.stop()
    w._external_reload()
    assert w._reload_pending and w._reload_timer.isActive()   # retried, not dropped
    w._own_write = 0
    w._external_reload()
    assert not w._reload_pending
    w.close()


def test_fit_refuses_model_that_cannot_be_saved(app, tmp_path, monkeypatch):
    from peakforge.gui import tasks
    from PySide6.QtWidgets import QMessageBox
    monkeypatch.setattr(QMessageBox, "exec", lambda self: 0)
    w, keys = _window_with_models(app, tmp_path)
    w.select_key(keys[0])
    before = w.project.get_model_record(keys[0])
    monkeypatch.setattr(w, "_store", lambda *a, **k: False)     # schema check refused the edit
    w.fit_current(1)
    assert not tasks.active()
    assert w.project.get_model_record(keys[0]) == before
    w.close()


def test_one_failing_spectrum_does_not_discard_the_others(app, tmp_path, monkeypatch):
    from peakforge.gui import tasks
    import peakforge.gui.window.jobs as jobs
    w, keys = _window_with_models(app, tmp_path)
    bad = w.project.spectra[keys[0]]
    real = jobs.prepare_for

    def prep(s, sh, m):
        if s is bad:
            raise IndexError("empty fit range")
        return real(s, sh, m)
    monkeypatch.setattr(jobs, "prepare_for", prep)
    w.fit_all()
    assert tasks.wait_tasks(app, 120)
    assert not _result_of(w.project, keys[0]) and _result_of(w.project, keys[1])
    w.close()


def test_shared_button_stays_disabled_until_last_task(app):
    import threading
    from PySide6.QtWidgets import QToolButton, QWidget
    from peakforge.gui import tasks
    host, b = QWidget(), QToolButton()
    gate = threading.Event()
    tasks.run_task(host, lambda: 1, lambda r: None, button_=b)
    tasks.run_task(host, lambda: gate.wait(30), lambda r: None, button_=b)
    end = __import__("time").monotonic() + 10
    while len(tasks._ACTIVE) > 1 and __import__("time").monotonic() < end:
        app.processEvents()
    assert len(tasks._ACTIVE) == 1 and not b.isEnabled()
    gate.set()
    assert tasks.wait_tasks(app, 30) and b.isEnabled()


def test_discarded_diagnosis_says_so(app, tmp_path):
    from peakforge.gui import tasks
    w, keys = _window_with_models(app, tmp_path)
    w.select_key(keys[0])
    w.diagnose_current()
    w.select_key(keys[1])
    assert tasks.wait_tasks(app, 120)
    assert keys[0] in w.diag_txt.toPlainText()
    w.close()
