"""File readers. ``load_file(path)`` returns a list of Spectrum objects."""
from __future__ import annotations

import os

from ..spectrum import Spectrum
from .phi_spe import read_spe
from .table import read_table
from .vamas import read_vamas

SUPPORTED = {".vms": "VAMAS", ".spe": "PHI SPE", ".csv": "CSV", ".txt": "Text",
             ".dat": "Text", ".xlsx": "Excel", ".xls": "Excel"}

FILE_FILTER = "XPS data (*.vms *.spe *.csv *.txt *.dat *.xlsx *.xls);;All files (*)"


def load_file(path: str) -> list[Spectrum]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".vms":
        return read_vamas(path)
    if ext == ".spe":
        return read_spe(path)
    if ext in (".csv", ".txt", ".dat", ".xlsx", ".xls", ".xlsm"):
        return read_table(path)
    # sniff
    with open(path, "rb") as f:
        head = f.read(16)
    if head.startswith(b"VAMAS"):
        return read_vamas(path)
    if head.startswith(b"SOFH"):
        return read_spe(path)
    raise ValueError(f"Unsupported file type: {path}")


__all__ = ["load_file", "read_vamas", "read_spe", "read_table", "SUPPORTED", "FILE_FILTER"]
