"""Single-figure export: formats, equality with the batch export, CLI, no pyplot."""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

EX = os.path.join(os.path.dirname(__file__), "..", "examples", "demo_fresh.csv")


@pytest.fixture()
def proj(tmp_path):
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_file(EX)
    k = p.keys("O 1s")[0]
    p.set_model(k, p.new_model(k))
    p.fit(k, n_starts=1)
    return p, k


@pytest.mark.parametrize("ext", [".png", ".svg", ".pdf", ".tif"])
def test_one_figure_each_format(proj, tmp_path, ext):
    from peakforge.export.exporter import export_one
    p, k = proj
    out = tmp_path / ("one" + ext)
    r = export_one(p, k, str(out), dpi=60)
    assert out.exists() and out.stat().st_size > 500 and r["path"] == str(out)


def test_transparent_png_has_alpha(proj, tmp_path):
    from matplotlib.image import imread
    from peakforge.export.exporter import export_one
    p, k = proj
    out = tmp_path / "t.png"
    export_one(p, k, str(out), dpi=60, transparent=True)
    assert imread(str(out))[..., 3].min() == 0


def test_one_equals_batch_pixels(proj, tmp_path):
    from matplotlib.image import imread
    import numpy as np
    from peakforge.export.exporter import export_all, export_one
    p, k = proj
    r = export_all(p, [k], out_dir=str(tmp_path / "b"), formats=("png",), dpi=70, stack=False)
    single = tmp_path / "s.png"
    export_one(p, k, str(single), dpi=70)
    batch = [f for f in r["figures"] if "compare" not in f and "combined" not in f][0]
    assert np.array_equal(imread(batch), imread(str(single)))


def test_origin_one_graph(proj, tmp_path):
    from peakforge.export.exporter import export_one
    p, k = proj
    r = export_one(p, k, str(tmp_path / "o" / "g.opju"))
    assert os.path.exists(r["origin"]["script"])    # data + builder always written; .opju only with Origin
    if r["origin"]["opju"]:
        assert os.path.abspath(r["origin"]["opju"]) == os.path.abspath(str(tmp_path / "o" / "g.opju"))
    assert os.path.exists(r["path"])                 # the .opju, or the build script without Origin
    assert len(list((tmp_path / "o").rglob("*.csv"))) == 1


def test_unknown_extension_and_unfitted(proj, tmp_path):
    from peakforge.export.exporter import export_one
    p, k = proj
    with pytest.raises(ValueError):
        export_one(p, k, str(tmp_path / "x.bmp"))
    other = [x for x in p.keys() if x != k][0]
    with pytest.raises(ValueError):
        export_one(p, other, str(tmp_path / "y.png"))


def test_cli_export_key(proj, tmp_path, capsys):
    from peakforge import cli
    p, k = proj
    out = tmp_path / "c.png"
    assert cli.main(["export", p.path, "--key", k, "--out", str(out), "--dpi", "60"]) == 0
    assert out.exists()


def test_gui_export_current(tmp_path, monkeypatch):
    pytest.importorskip("PySide6")
    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtWidgets import QApplication, QFileDialog
    from peakforge.gui import tasks
    from peakforge.gui.main_window import MainWindow
    from peakforge.project import Project
    app = QApplication.instance() or QApplication([])
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_file(EX)
    k = p.keys("O 1s")[0]
    p.set_model(k, p.new_model(k))
    p.fit(k, n_starts=1)
    w = MainWindow(p.path)
    w.select_key(k)
    out = tmp_path / "gui.svg"
    monkeypatch.setattr(QFileDialog, "getSaveFileName", staticmethod(lambda *a, **kw: (str(out), "")))
    w.export_current()
    assert tasks.wait_tasks(app, 60)
    assert out.exists()
    w.close()
