"""CSV / TXT / Excel reader.

Accepted layouts (auto-detected):
  * pairs of columns  BE, I, BE, I, ... ; an optional first row with region names
    (e.g. 'Ir 4f'), optional second row with column titles;
  * a single BE column followed by several intensity columns (column titles = region / sample).
Binding energy is assumed unless a header contains 'kinetic'.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from ..spectrum import Spectrum, normalize_region


def _frames(path: str) -> list[tuple[str, pd.DataFrame]]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        book = pd.read_excel(path, sheet_name=None, header=None)
        return list(book.items())
    sep = None
    with open(path, "r", encoding="utf-8-sig", errors="replace") as f:
        head = f.read(4096)
    if "\t" in head:
        sep = "\t"
    elif "," in head:
        sep = ","
    df = pd.read_csv(path, header=None, sep=sep, engine="python", encoding="utf-8-sig",
                     comment="#", skip_blank_lines=True)
    return [(os.path.splitext(os.path.basename(path))[0], df)]


def _first_numeric_row(df: pd.DataFrame) -> int:
    for r in range(min(len(df), 20)):
        v = pd.to_numeric(df.iloc[r], errors="coerce")
        if v.notna().sum() >= 2:
            return r
    return 0


def read_table(path: str, hv: float = 1486.6) -> list[Spectrum]:
    base = os.path.splitext(os.path.basename(path))[0]
    out: list[Spectrum] = []
    for sheet, df in _frames(path):
        df = df.dropna(how="all", axis=1).dropna(how="all", axis=0).reset_index(drop=True)
        if df.empty:
            continue
        r0 = _first_numeric_row(df)
        heads = df.iloc[:r0].astype(str).fillna("") if r0 else None
        num = df.iloc[r0:].apply(pd.to_numeric, errors="coerce")
        ncol = num.shape[1]

        def title(c: int) -> str:
            if heads is None:
                return ""
            parts = [str(heads.iloc[r, c]) for r in range(heads.shape[0])
                     if str(heads.iloc[r, c]) not in ("nan", "", "None")]
            return parts[0] if parts else ""

        kinetic = heads is not None and any("kinetic" in str(v).lower() for v in heads.values.ravel())
        # decide layout: monotonic columns are energy axes
        mono = [bool(num.iloc[:, c].dropna().is_monotonic_increasing or
                     num.iloc[:, c].dropna().is_monotonic_decreasing) for c in range(ncol)]
        pairs: list[tuple[int, int]] = []
        if ncol >= 2 and ncol % 2 == 0 and all(mono[0::2]):
            pairs = [(c, c + 1) for c in range(0, ncol, 2)]
        else:
            pairs = [(0, c) for c in range(1, ncol)]
        for k, (cx, cy) in enumerate(pairs):
            m = num.iloc[:, cx].notna() & num.iloc[:, cy].notna()
            x = num.iloc[:, cx][m].to_numpy(float)
            y = num.iloc[:, cy][m].to_numpy(float)
            if len(x) < 5:
                continue
            lab = title(cx) if len(pairs) > 1 and (ncol % 2 == 0) else title(cy)
            if not lab or lab.lower().startswith(("binding", "be", "energy", "kinetic", "unnamed")):
                lab = title(cy) or f"{sheet} {k + 1}"
            be = hv - x if kinetic else x
            out.append(Spectrum(region=normalize_region(lab), be=be, cps=y,
                                sample=base if len(_frames(path)) == 1 else f"{base}:{sheet}",
                                source_file=path, meta=dict(format="table", sheet=sheet)))
    return out
