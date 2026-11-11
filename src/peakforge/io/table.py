"""CSV / TXT / Excel reader.

Without a template the layout is auto-detected:
  * pairs of columns  BE, I, BE, I, ... ; an optional first row with region names
    (e.g. 'Ir 4f'), optional second row with column titles;
  * a single BE column followed by several intensity columns (column titles = region / sample).
  Binding energy and counts per second are assumed unless a header contains 'kinetic'.

With a column template (built by the column-mapping wizard, stored in the project under
"formats"; full description in docs/METHODS*.md §"Acquisition time"):
  {"base": "table", "x": <column>, "y": [<column>, ...] (empty = all other numeric columns),
   "energy": "binding" | "kinetic", "hv": 1486.6,
   "intensity": "cps" | "counts", "acq_time": <s per point or null>,
   "regions": {"<column>": "Ir 4f"}, "sheet": "<Excel sheet>" }
A <column> is the header text (when it is unique in the file) or the 0-based column number.
"counts" with acq_time t → cps = counts / t and Poisson weights use t; "counts" without a time
keeps the numbers as they are and uses t = 1 s, so the Poisson noise model is exact.
"""
from __future__ import annotations

import os

import pandas as pd

from ..spectrum import Spectrum, normalize_region

TEMPLATE_KEYS = {"base", "x", "y", "energy", "hv", "intensity", "acq_time", "regions", "sheet", "note"}


def _frames(path: str) -> list[tuple[str, pd.DataFrame]]:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".xlsx", ".xls", ".xlsm"):
        book = pd.read_excel(path, sheet_name=None, header=None)
        return list(book.items())
    enc = text_encoding(path)
    with open(path, "r", encoding=enc, errors="replace") as f:
        head = f.read(4096)
    sep = None
    if "\t" in head:
        sep = "\t"
    elif "," in head:
        sep = ","
    elif ";" in head:
        sep = ";"
    else:
        sep = r"\s+"
    df = pd.read_csv(path, header=None, sep=sep, engine="python", encoding=enc,
                     encoding_errors="replace", comment="#", skip_blank_lines=True)
    return [(os.path.splitext(os.path.basename(path))[0], df)]


def text_encoding(path: str) -> str:
    """UTF-8 (with or without BOM) if the file decodes as such, else GB18030 (Chinese Windows /
    Excel 'CSV'), else Latin-1. Only header text depends on this; numbers are ASCII in all three."""
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "gb18030"):
        try:
            raw.decode(enc)
            return enc
        except UnicodeDecodeError:
            continue
    return "latin-1"


def _first_numeric_row(df: pd.DataFrame) -> int:
    for r in range(min(len(df), 20)):
        v = pd.to_numeric(df.iloc[r], errors="coerce")
        if v.notna().sum() >= 2:
            return r
    return 0


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    return df.dropna(how="all", axis=1).dropna(how="all", axis=0).reset_index(drop=True)


def split_frame(df: pd.DataFrame) -> tuple[list[str], pd.DataFrame]:
    """-> (column names, numeric block). A column name joins the non-empty header cells with ' / '
    ('' when the file has no header)."""
    df = _clean(df)
    r0 = _first_numeric_row(df)
    names = []
    for c in range(df.shape[1]):
        parts = [str(df.iloc[r, c]).strip() for r in range(r0)]
        parts = [p for p in parts if p not in ("nan", "", "None")]
        names.append(" / ".join(parts))
    num = df.iloc[r0:].apply(pd.to_numeric, errors="coerce").reset_index(drop=True)
    num.columns = range(num.shape[1])
    return names, num


def sheets(path: str) -> list[tuple[str, list[str], pd.DataFrame]]:
    """[(sheet, column names, numeric block)] for every non-empty sheet (one for text files)."""
    out = []
    for sheet, df in _frames(path):
        if _clean(df).empty:
            continue
        names, num = split_frame(df)
        out.append((str(sheet), names, num))
    return out


def column_index(ref, names: list[str]) -> int:
    """Template column reference (header text or 0-based number) -> column number."""
    if isinstance(ref, bool):
        raise ValueError(f"bad column reference {ref!r}")
    if isinstance(ref, int) or (isinstance(ref, str) and ref.strip().isdigit() and ref not in names):
        i = int(ref)
        if not 0 <= i < len(names):
            raise ValueError(f"column {i} does not exist (the file has {len(names)} columns)")
        return i
    hits = [i for i, n in enumerate(names) if n == ref]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise ValueError(f"no column named '{ref}' (columns: {names})")
    raise ValueError(f"column name '{ref}' is not unique; use its number")


def read_table(path: str, hv: float = 1486.6, template: dict | None = None) -> list[Spectrum]:
    if template is not None:
        return _read_template(path, template)
    base = os.path.splitext(os.path.basename(path))[0]
    out: list[Spectrum] = []
    frames = _frames(path)
    for sheet, df in frames:
        df = _clean(df)
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
                                sample=base if len(frames) == 1 else f"{base}:{sheet}",
                                source_file=path, meta=dict(format="table", sheet=sheet)))
    return out


def check_template(tpl: dict) -> list[str]:
    """Structural problems of a column template (empty list = fine)."""
    errs = []
    unknown = set(tpl) - TEMPLATE_KEYS
    if unknown:
        errs.append(f"unknown keys {sorted(unknown)}")
    if tpl.get("base", "table") != "table":
        errs.append(f"base must be 'table', not {tpl.get('base')!r}")
    if "x" not in tpl:
        errs.append("'x' (energy column) is required")
    if tpl.get("energy", "binding") not in ("binding", "kinetic"):
        errs.append(f"energy must be 'binding' or 'kinetic', not {tpl.get('energy')!r}")
    if tpl.get("intensity", "cps") not in ("cps", "counts"):
        errs.append(f"intensity must be 'cps' or 'counts', not {tpl.get('intensity')!r}")
    t = tpl.get("acq_time")
    if t is not None and (not isinstance(t, (int, float)) or isinstance(t, bool) or t <= 0):
        errs.append(f"acq_time must be a positive number of seconds, not {t!r}")
    hv = tpl.get("hv", 1486.6)
    if not isinstance(hv, (int, float)) or isinstance(hv, bool) or hv <= 0:
        errs.append(f"hv must be a positive photon energy in eV, not {hv!r}")
    y = tpl.get("y", [])
    if not isinstance(y, list):
        errs.append("'y' must be a list of columns")
    if not isinstance(tpl.get("regions", {}), dict):
        errs.append("'regions' must map column -> region")
    return errs


def _read_template(path: str, tpl: dict) -> list[Spectrum]:
    errs = check_template(tpl)
    if errs:
        raise ValueError("column template: " + "; ".join(errs))
    base = os.path.splitext(os.path.basename(path))[0]
    tabs = sheets(path)
    if tpl.get("sheet"):
        tabs = [t for t in tabs if t[0] == str(tpl["sheet"])]
        if not tabs:
            raise ValueError(f"no sheet named '{tpl['sheet']}'")
    if not tabs:
        raise ValueError("no data in the file")
    kinetic = tpl.get("energy", "binding") == "kinetic"
    hv = float(tpl.get("hv", 1486.6))
    counts = tpl.get("intensity", "cps") == "counts"
    t = tpl.get("acq_time")
    regions = {str(k): v for k, v in (tpl.get("regions") or {}).items()}
    out: list[Spectrum] = []
    for sheet, names, num in tabs:
        cx = column_index(tpl["x"], names)
        ys = [column_index(r, names) for r in tpl.get("y") or []]
        if not ys:
            ys = [c for c in range(num.shape[1]) if c != cx and num.iloc[:, c].notna().sum() >= 5]
        for cy in ys:
            if cy == cx:
                raise ValueError("an intensity column is the energy column")
            m = num.iloc[:, cx].notna() & num.iloc[:, cy].notna()
            x = num.iloc[:, cx][m].to_numpy(float)
            y = num.iloc[:, cy][m].to_numpy(float)
            if len(x) < 5:
                continue
            ref = next((regions[k] for k in (names[cy], str(cy)) if k in regions), None)
            lab = ref or names[cy] or f"{sheet} {cy}"
            meta = dict(format="table", sheet=sheet, y_unit="counts" if counts else "cps",
                        columns=dict(x=names[cx] or cx, y=names[cy] or cy))
            if counts:
                tt = float(t) if t else 1.0
                y = y / tt
                meta["acq_time"] = tt
            elif t:
                meta["acq_time"] = float(t)
            if kinetic:
                meta["photon_energy"] = hv
            out.append(Spectrum(region=normalize_region(str(lab).split(" / ")[0]),
                                be=hv - x if kinetic else x, cps=y,
                                sample=base if len(tabs) == 1 else f"{base}:{sheet}",
                                source_file=path, meta=meta))
    if not out:
        raise ValueError("the template selected no column with at least 5 numeric points")
    return out
