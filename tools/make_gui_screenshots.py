"""Screenshots of the GUI for the GUI guide (src/peakforge/docs/images/gui_*.png), offscreen, English UI.

Built from the synthetic demo data in examples/ only (no instrument data). The language is switched in memory
only: ~/.peakforge/settings.json is not touched.

    python tools/make_demo_data.py          # once, creates examples/demo_*.csv
    python tools/make_gui_screenshots.py
"""
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", "C:/Windows/Fonts")      # offscreen has no system fonts otherwise
os.environ["QT_SCALE_FACTOR"] = "2"     # 2x pixels: the help reader shows images at half size (gui/help.py IMG_SCALE)
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, os.path.join(ROOT, "src"))
OUT = os.path.join(ROOT, "src", "peakforge", "docs", "images")

from PySide6.QtWidgets import QApplication  # noqa: E402

from peakforge.gui import i18n  # noqa: E402

i18n._lang = "en"                      # in memory only
app = QApplication.instance() or QApplication([])

from peakforge.gui.colwizard import ColumnWizard  # noqa: E402
from peakforge.gui.dialogs import ExportDialog  # noqa: E402
from peakforge.gui.help import HelpWindow  # noqa: E402
from peakforge.gui.main_window import MainWindow  # noqa: E402
from peakforge.gui.style import QSS  # noqa: E402
from peakforge.gui.tasks import wait_tasks  # noqa: E402
from peakforge.project import Project  # noqa: E402

app.setStyle("Fusion")
app.setStyleSheet(QSS)


def shot(w, name):
    w.show()
    app.processEvents()
    w.grab().save(os.path.join(OUT, name))
    print("wrote", name)


def main():
    tmp = tempfile.mkdtemp(prefix="pf_shots_")
    p = Project.create(os.path.join(tmp, "demo"), "Demo")
    for f, lab in (("demo_fresh", "Fresh"), ("demo_aged", "Aged")):
        p.add_file(os.path.join(ROOT, "examples", f + ".csv"))
        p.set_sample_label(f, lab)
    p.auto_charge()
    w = MainWindow(p.path)
    w.resize(1500, 900)
    key = p.keys("Ir 4f")[0]
    w.select_key(key)
    w._preset_requested("")
    w.fit_current(3)
    wait_tasks(app, 120)
    w.tabs.setCurrentWidget(w.res_tab)
    shot(w, "gui_main.png")
    w.diagnose_current()
    wait_tasks(app, 180)
    w.tabs.setCurrentWidget(w.diag_txt)
    w.grab()
    w.panel.grab().save(os.path.join(OUT, "gui_model_panel.png"))
    w.tree.grab().save(os.path.join(OUT, "gui_tree.png"))
    w.tabs.grab().save(os.path.join(OUT, "gui_diagnostics.png"))
    d = ExportDialog(p, w)
    shot(d, "gui_export.png")
    d.close()
    ColumnWizard(os.path.join(ROOT, "examples", "demo_fresh.csv"), parent=w).grab().save(os.path.join(OUT, "gui_wizard.png"))
    h = HelpWindow(w)
    shot(h, "gui_help.png")
    h.close()
    w.close()


if __name__ == "__main__":
    main()
