"""Reader plug-in table. Every file format is a ``Reader`` with ``detect`` + ``read``.

    detect(path, head) -> int      confidence 0–100 from the suffix and the first 4 kB (bytes);
                                   < 30 means "not mine"
    read(path, template=None) -> list[Spectrum]

``read_file(path)`` picks the most confident reader. Tables can also be read with a *column
template* (a dict saved in the project under ``"formats"``, built by the column-mapping wizard,
see ``io/wizard.py``); the template's ``"base"`` names the reader that understands it.
A new format needs only a new Reader appended to ``REGISTRY``.
"""
from __future__ import annotations

import os

from ..spectrum import Spectrum


class ReadError(ValueError):
    """A file could not be read. ``str(e)`` is English; ``e.zh`` is the Chinese message."""

    def __init__(self, en: str, zh: str | None = None):
        super().__init__(en)
        self.en, self.zh = en, zh or en

    def text(self, lang: str = "en") -> str:
        return self.zh if lang == "zh" else self.en


class Reader:
    name = ""                       # stable id stored in project files
    label = ("", "")                # (zh, en) shown in the GUI
    suffixes: tuple[str, ...] = ()

    def detect(self, path: str, head: bytes) -> int:
        return 0

    def read(self, path: str, template: dict | None = None) -> list[Spectrum]:
        raise NotImplementedError

    def companions(self, path: str) -> list[str]:
        """Other files/folders that belong to `path` and must be copied with it into a project."""
        return []


class VamasReader(Reader):
    name, label, suffixes = "vamas", ("VAMAS (ISO 14976)", "VAMAS (ISO 14976)"), (".vms", ".vamas")

    def detect(self, path, head):
        if head.startswith(b"VAMAS Surface Chemical Analysis Standard"):
            return 100
        return 60 if os.path.splitext(path)[1].lower() in self.suffixes else 0

    def read(self, path, template=None):
        from .vamas import read_vamas
        return read_vamas(path)


class PhiSpeReader(Reader):
    name, label, suffixes = "phi_spe", ("PHI MultiPak .spe", "PHI MultiPak .spe"), (".spe",)

    def detect(self, path, head):
        if head.startswith(b"SOFH"):
            return 100
        return 60 if os.path.splitext(path)[1].lower() in self.suffixes else 0

    def read(self, path, template=None):
        from .phi_spe import read_spe
        return read_spe(path)


class TableReader(Reader):
    name, label = "table", ("表格（CSV / TXT / Excel）", "Table (CSV / TXT / Excel)")
    suffixes = (".csv", ".txt", ".dat", ".xy", ".xlsx", ".xls", ".xlsm")

    def detect(self, path, head):
        if os.path.splitext(path)[1].lower() in self.suffixes:
            return 50
        # unknown suffix: plain text whose first non-empty lines look numeric
        try:
            text = head.decode("utf-8", errors="strict")
        except UnicodeDecodeError:
            return 0
        lines = [ln for ln in text.splitlines()[:40] if ln.strip()]
        num = sum(1 for ln in lines if _numeric_line(ln))
        return 35 if num >= 5 else 0

    def read(self, path, template=None):
        from .table import read_table
        return read_table(path, template=template)


class ThermoVgdReader(Reader):
    name, label = "thermo_vgd", ("Thermo Avantage（.vgp 实验 / .VGD）", "Thermo Avantage (.vgp experiment / .VGD)")
    suffixes = (".vgp", ".vgd")

    def detect(self, path, head):
        ext = os.path.splitext(path)[1].lower()
        if ext not in self.suffixes:            # .xls is OLE2 too: decide by suffix
            return 0
        return 95 if head.startswith(bytes.fromhex("d0cf11e0a1b11ae1")) else 40

    def read(self, path, template=None):
        from .thermo_vgd import VGDError, read_experiment
        try:
            sps = read_experiment(path)
        except VGDError as e:
            raise ReadError(f"{os.path.basename(path)}: {e}", f"{os.path.basename(path)}：{e}") from e
        if not sps:
            raise ReadError(f"{os.path.basename(path)}: the experiment contains no spectra",
                            f"{os.path.basename(path)}：该实验中没有谱")
        return sps

    def companions(self, path):
        if path.lower().endswith(".vgp"):
            from .thermo_vgd import VGDError, data_folder
            try:
                return [data_folder(path)]
            except VGDError:
                return []
        return []


def _numeric_line(line: str) -> bool:
    import re
    toks = [t for t in re.split(r"[\s,;]+", line.strip()) if t]
    if len(toks) < 2:
        return False
    try:
        [float(t) for t in toks]
    except ValueError:
        return False
    return True


REGISTRY: list[Reader] = [VamasReader(), PhiSpeReader(), ThermoVgdReader(), TableReader()]
BY_NAME = {r.name: r for r in REGISTRY}
# names written by older versions in project "files[].format" / Spectrum.meta["format"]
ALIASES = {"VAMAS": "vamas", "PHI SPE": "phi_spe"}


def list_formats() -> list[dict]:
    return [dict(name=r.name, zh=r.label[0], en=r.label[1], suffixes=list(r.suffixes)) for r in REGISTRY]


def file_filter() -> str:
    pats = " ".join(f"*{s}" for r in REGISTRY for s in r.suffixes)
    return f"XPS data ({pats});;All files (*)"


def _head(path: str, n: int = 4096) -> bytes:
    try:
        with open(path, "rb") as f:
            return f.read(n)
    except OSError as e:
        raise ReadError(f"Cannot open {os.path.basename(path)}: {e}",
                        f"无法打开 {os.path.basename(path)}：{e}") from None


def detect_format(path: str) -> tuple[str | None, int]:
    """-> (reader name, confidence); (None, best score) when no reader is confident (score < 30)."""
    head = _head(path)
    best, score = None, 0
    for r in REGISTRY:
        s = r.detect(path, head)
        if s > score:
            best, score = r.name, s
    return (best, score) if score >= 30 else (None, score)


def resolve(fmt: str | None, templates: dict | None = None) -> tuple[str | None, dict | None]:
    """fmt is a reader name or the name of a template in ``templates`` -> (reader name, template)."""
    if not fmt:
        return None, None
    templates = templates or {}
    if fmt in templates:
        tpl = dict(templates[fmt])
        return tpl.get("base", "table"), tpl
    return ALIASES.get(fmt, fmt), None


def read_file(path: str, fmt: str | None = None, templates: dict | None = None,
              template: dict | None = None) -> list[Spectrum]:
    """Read every spectrum in a file. ``fmt``: reader name or template name (None = detect);
    ``template``: an explicit column template (overrides ``fmt``)."""
    name = os.path.basename(path)
    if not os.path.exists(path):
        raise ReadError(f"File not found: {path}", f"找不到文件：{path}")
    if template is not None:
        rname = template.get("base", "table")
    else:
        rname, template = resolve(fmt, templates)
        if fmt and rname not in BY_NAME:
            raise ReadError(f"{name}: unknown format or template '{fmt}' (formats: {', '.join(BY_NAME)})",
                            f"{name}：未知的格式或模板“{fmt}”（可用格式：{', '.join(BY_NAME)}）")
    if not rname:
        rname, score = detect_format(path)
        if not rname:
            raise ReadError(f"{name}: unknown file format (confidence {score}). For a table, use "
                            "'Import with column mapping'.",
                            f"{name}：无法识别文件格式（置信度 {score}）。表格数据请用“按列映射导入”。")
    if rname not in BY_NAME:
        raise ReadError(f"{name}: unknown format '{rname}'", f"{name}：未知格式“{rname}”")
    try:
        sps = BY_NAME[rname].read(path, template=template)
    except ReadError:
        raise
    except Exception as e:      # noqa: BLE001 — any reader failure (BadZipFile, struct.error, missing
        # openpyxl, ...) is a per-file problem: callers skip the file instead of failing the project
        raise ReadError(f"{name}: could not be read as {rname}: {e}",
                        f"{name}：按 {BY_NAME[rname].label[0]} 读入失败：{e}") from e
    for s in sps:
        s.meta.setdefault("reader", rname)
    return sps
