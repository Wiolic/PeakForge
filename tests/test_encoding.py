"""Static check: every text-mode file I/O names its encoding.

Without it Python uses the locale code page (cp936 / cp1252 on Windows), so a file written on a
Chinese system breaks on an English one and vice versa (XAFSmith 1.0.0 crashed this way).
Checked calls: open(), Path.read_text/write_text/open, pandas read_csv/to_csv/read_table,
subprocess with text=True / universal_newlines=True, io.TextIOWrapper.
"""
from __future__ import annotations

import ast
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIRS = ("src", "tests", "tools")
SKIP_PARTS = ("__pycache__", ".venv", "local")


def _py_files():
    for d in DIRS:
        for base, dirs, files in os.walk(os.path.join(ROOT, d)):
            dirs[:] = [x for x in dirs if x not in SKIP_PARTS]
            for f in files:
                if f.endswith(".py"):
                    yield os.path.join(base, f)
    for f in os.listdir(ROOT):
        if f.endswith(".py"):
            yield os.path.join(ROOT, f)


def _kw(call: ast.Call, name: str):
    return next((k.value for k in call.keywords if k.arg == name), None)


def _const(node):
    return node.value if isinstance(node, ast.Constant) else None


def _has_kwargs(call: ast.Call) -> bool:
    return any(k.arg is None for k in call.keywords)       # **kw: can't tell statically


def problems(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        tree = ast.parse(f.read(), path)
    out = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call) or _has_kwargs(n):
            continue
        fn = n.func
        name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ""
        where = f"{os.path.basename(path)}:{n.lineno}"
        if name == "open" and (isinstance(fn, ast.Name) or isinstance(fn, ast.Attribute)):
            if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) and fn.value.id in ("os", "zipfile", "z", "zf"):
                continue
            mode = _kw(n, "mode") or (n.args[1] if len(n.args) > 1 else None)
            if isinstance(fn, ast.Attribute):        # Path.open(mode); skip Class.open(path) factories
                if isinstance(fn.value, ast.Name) and fn.value.id[:1].isupper():
                    continue
                mode = _kw(n, "mode") or (n.args[0] if n.args else None)
                if mode is not None and _const(mode) is None:
                    continue
            m = _const(mode) if mode is not None else "r"
            if isinstance(m, str) and "b" in m:
                continue
            if mode is not None and m is None:
                out.append(f"{where}: open() with a non-literal mode — pass encoding= explicitly")
                continue
            if _kw(n, "encoding") is None and not (len(n.args) > 3):
                out.append(f"{where}: open() in text mode without encoding=")
        elif name in ("read_text", "write_text") and isinstance(fn, ast.Attribute):
            if _kw(n, "encoding") is None and len(n.args) < (2 if name == "write_text" else 1):
                out.append(f"{where}: {name}() without encoding=")
        elif name in ("read_csv", "to_csv", "read_table", "read_fwf") and isinstance(fn, ast.Attribute):
            if _kw(n, "encoding") is None:
                out.append(f"{where}: pandas {name}() without encoding=")
        elif name in ("run", "check_output", "Popen", "check_call", "call") and isinstance(fn, ast.Attribute) \
                and isinstance(fn.value, ast.Name) and fn.value.id == "subprocess":
            text = _const(_kw(n, "text")) or _const(_kw(n, "universal_newlines"))
            if text and _kw(n, "encoding") is None:
                out.append(f"{where}: subprocess {name}(text=True) without encoding=")
        elif name == "TextIOWrapper" and _kw(n, "encoding") is None:
            out.append(f"{where}: TextIOWrapper without encoding=")
    return out


def test_checker_catches_examples(tmp_path):
    bad = tmp_path / "bad.py"
    bad.write_text("open('a')\nopen('a', 'w')\nimport pandas as pd\npd.read_csv('x')\n"
                   "from pathlib import Path\nPath('a').read_text()\nopen('a', 'rb')\n"
                   "open('a', encoding='utf-8')\n", encoding="utf-8")
    assert len(problems(str(bad))) == 4


@pytest.mark.parametrize("path", sorted(set(_py_files())), ids=lambda p: os.path.relpath(p, ROOT))
def test_text_io_names_encoding(path):
    assert problems(path) == []
