"""Back end of the column-mapping wizard (no Qt; tested on its own).

inspect_table(path)  -> preview of every sheet with a first guess of the mapping
build_template(...)  -> column template dict (see io/table.py)
try_read(path, tpl)  -> short summary of what the template reads
add_template(project_data, name, tpl) stores it under project "formats".
"""
from __future__ import annotations

import numpy as np

from .registry import BY_NAME, ReadError
from .table import check_template, sheets

_KINETIC = ("kinetic", "ke", "k.e.")
_COUNTS = ("counts", "count", "cts")


def _guess(names: list[str], num) -> dict:
    ncol = num.shape[1]
    mono = []
    for c in range(ncol):
        v = num.iloc[:, c].dropna()
        mono.append(len(v) >= 5 and bool(v.is_monotonic_increasing or v.is_monotonic_decreasing))
    low = [n.lower() for n in names]
    x = next((c for c in range(ncol) if mono[c] and any(k in low[c] for k in ("energy", "be", "ke", "ev"))),
             next((c for c in range(ncol) if mono[c]), 0))
    energy = "kinetic" if any(k in low[x] for k in _KINETIC) else "binding"
    ys = [c for c in range(ncol) if c != x and not mono[c] and num.iloc[:, c].notna().sum() >= 5]
    intensity = "counts" if any(any(k in low[c] for k in _COUNTS) and "/s" not in low[c] and "cps" not in low[c]
                                for c in ys) else "cps"
    return dict(x=x, y=ys, energy=energy, intensity=intensity)


def inspect_table(path: str, nrows: int = 10) -> list[dict]:
    """[{sheet, names, ncols, ntotal, rows (first nrows, NaN → None), guess}] — one per sheet."""
    try:
        tabs = sheets(path)
    except (ValueError, OSError, UnicodeDecodeError) as e:
        raise ReadError(f"Cannot read the table: {e}", f"无法读取表格：{e}") from e
    out = []
    for sheet, names, num in tabs:
        rows = [[None if (isinstance(v, float) and np.isnan(v)) else float(v) for v in r]
                for r in num.head(nrows).itertuples(index=False)]
        out.append(dict(sheet=sheet, names=names, ncols=int(num.shape[1]), ntotal=int(num.shape[0]),
                        rows=rows, guess=_guess(names, num)))
    if not out:
        raise ReadError("The file contains no numeric table", "文件中没有数值表格")
    return out


def _ref(i: int, names: list[str]):
    """Header text when it is unique (survives reordered columns), otherwise the column number."""
    n = names[i] if 0 <= i < len(names) else ""
    return n if n and names.count(n) == 1 and not n.strip().isdigit() else i


def build_template(names: list[str], x: int, y: list[int] | None = None, energy: str = "binding",
                   hv: float = 1486.6, intensity: str = "cps", acq_time: float | None = None,
                   regions: dict[int, str] | None = None, sheet: str | None = None) -> dict:
    tpl: dict = dict(base="table", x=_ref(int(x), names), y=[_ref(int(c), names) for c in (y or [])],
                     energy=energy, intensity=intensity)
    if energy == "kinetic":
        tpl["hv"] = float(hv)
    if acq_time:
        tpl["acq_time"] = float(acq_time)
    if regions:
        tpl["regions"] = {str(_ref(int(c), names)): r for c, r in regions.items() if r}
    if sheet:
        tpl["sheet"] = sheet
    if int(x) in [int(c) for c in (y or [])]:
        raise ReadError("The energy column cannot also be an intensity column", "能量列不能同时是强度列")
    errs = check_template(tpl)
    if errs:
        raise ReadError("; ".join(errs))
    return tpl


def try_read(path: str, tpl: dict) -> list[dict]:
    from .registry import read_file
    sps = read_file(path, template=tpl)
    return [dict(region=s.region, npts=int(len(s.be)), be_min=float(s.be.min()), be_max=float(s.be.max()),
                 y_min=float(s.cps.min()), y_max=float(s.cps.max()), acq_time=s.acq_time()) for s in sps]


def add_template(project_data: dict, name: str, tpl: dict) -> dict:
    name = (name or "").strip()
    if not name:
        raise ReadError("Give the template a name", "请给模板起个名字")
    if name in BY_NAME:
        raise ReadError(f"'{name}' is a built-in format name", f"“{name}”是内置格式名，请换一个名字")
    project_data.setdefault("formats", {})[name] = tpl
    return project_data
