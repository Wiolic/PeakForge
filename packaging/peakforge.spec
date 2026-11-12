# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: onedir, two executables sharing one set of dependencies
#   PeakForge.exe       windowed (no console; double-click opens the GUI)
#   peakforge-cli.exe   console (command line / AI agents: `peakforge-cli.exe mcp`)
# Build (from the repo root):  python -m PyInstaller packaging/peakforge.spec --noconfirm
import os
ROOT = os.path.dirname(SPECPATH)
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

datas, binaries, hiddenimports = [], [], []
d, b, h = collect_all("peakforge")
datas += d; binaries += b; hiddenimports += h
# mcp: skip mcp.cli (needs the optional `typer`; importing it during analysis aborts the build)
hiddenimports += collect_submodules("mcp", filter=lambda n: not n.startswith("mcp.cli"))
datas += collect_data_files("mcp")
# docs (md + images), presets/data, assets are package data and come with collect_all("peakforge").
# origin_builder.py is *copied* next to exported data and run inside Origin, so it must exist as a real .py file.
datas += [(os.path.join(ROOT, "src", "peakforge", "export", "origin_builder.py"), "peakforge/export")]
hiddenimports += ["matplotlib.backends.backend_qtagg", "matplotlib.backends.backend_agg", "PySide6.QtSvg",
                  "openpyxl.cell._writer"]

excludes = [
    "tkinter", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick", "PySide6.QtPdf",
    "PySide6.QtPdfWidgets", "PySide6.QtQuick", "PySide6.QtQml", "PySide6.Qt3DCore", "PySide6.QtMultimedia",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtBluetooth", "PySide6.QtNetworkAuth",
    "mcp.cli", "typer", "IPython", "notebook", "jupyter", "pytest", "originpro", "win32com", "pythoncom",
    # MKL / large optional packages that numpy/scipy/pandas never need at run time
    "mkl", "mkl_fft", "pyarrow", "sklearn", "skimage", "plotly", "botocore", "boto3", "mypy",
]


def analysis(entry):
    return Analysis([entry], pathex=[os.path.join(ROOT, "src")], binaries=binaries, datas=datas, hiddenimports=hiddenimports,
                    excludes=excludes, noarchive=False)


# Python UTF-8 mode as a safety net: English Windows defaults to cp1252 (all text I/O in the code names encoding= anyway).
PYOPTS = [("X utf8_mode=1", None, "OPTION")]
ICON = os.path.join(ROOT, "src", "peakforge", "assets", "peakforge.ico")

a_gui = analysis(os.path.join(ROOT, "packaging", "peakforge_gui_entry.py"))
a_cli = analysis(os.path.join(ROOT, "packaging", "peakforge_cli_entry.py"))
pyz_gui = PYZ(a_gui.pure)
pyz_cli = PYZ(a_cli.pure)

exe_gui = EXE(pyz_gui, a_gui.scripts, PYOPTS, exclude_binaries=True, name="PeakForge", console=False, icon=ICON,
              contents_directory="_internal")
exe_cli = EXE(pyz_cli, a_cli.scripts, PYOPTS, exclude_binaries=True, name="peakforge-cli", console=True, icon=ICON,
              contents_directory="_internal")


def _keep(item):
    dest = item[0].replace("\\", "/")
    if dest.endswith("direct_url.json"):       # `pip install -e` marker: holds the build machine's path, marks a dev install
        return False
    if "PySide6/translations/" in dest:        # keep Chinese and English Qt translations only
        n = dest.rsplit("/", 1)[-1]
        return any(k in n for k in ("_zh_CN", "_en"))
    return True


for _a in (a_gui, a_cli):
    _a.datas = [d for d in _a.datas if _keep(d)]
    _a.binaries = [b for b in _a.binaries if not b[0].lower().startswith(("mkl", "libiomp5md"))]

coll = COLLECT(exe_gui, a_gui.binaries, a_gui.datas,
               exe_cli, a_cli.binaries, a_cli.datas,
               name="PeakForge")
