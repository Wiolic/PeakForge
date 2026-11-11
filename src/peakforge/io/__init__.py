"""File readers. ``load_file(path)`` returns a list of Spectrum objects.

Formats are plug-ins in ``io/registry.py`` (``REGISTRY``); ``read_file`` also accepts a reader
name, a project column-template name or an explicit template (see ``io/table.py``).
"""
from __future__ import annotations

from ..spectrum import Spectrum
from .phi_spe import read_spe
from .registry import (BY_NAME, REGISTRY, ReadError, Reader, detect_format, file_filter, list_formats,
                       read_file)
from .table import read_table
from .vamas import read_vamas

SUPPORTED = {s: r.label[1] for r in REGISTRY for s in r.suffixes}
FILE_FILTER = file_filter()


def load_file(path: str, fmt: str | None = None, templates: dict | None = None) -> list[Spectrum]:
    return read_file(path, fmt=fmt, templates=templates)


__all__ = ["load_file", "read_file", "detect_format", "list_formats", "ReadError", "Reader", "REGISTRY",
           "BY_NAME", "read_vamas", "read_spe", "read_table", "SUPPORTED", "FILE_FILTER"]
