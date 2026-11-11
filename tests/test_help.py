"""In-app help documents (src/peakforge/docs): zh/en pairs, structure, images, links, formulas, and the
numbers quoted from the orbital table. The HelpWindow itself is tested separately (gui/help.py)."""
from __future__ import annotations

import json
import os
import re

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "src", "peakforge", "docs")
ORBITALS = os.path.join(ROOT, "src", "peakforge", "data", "orbitals.json")

PAIRS = [("XPS基础讲义.md", "XPS_basics_en.md"),
         ("零基础XPS拟合教程.md", "fitting_tutorial_en.md"),
         ("图形界面使用指南.md", "GUI_guide_en.md")]
# Written in a later step of phase 3.5; links to them are allowed while they do not exist yet.
PENDING = {"图形界面使用指南.md", "GUI_guide_en.md"}


def _read(name: str) -> str:
    with open(os.path.join(DOCS, name), encoding="utf-8") as f:
        return f.read()


def _present() -> list[str]:
    return [f for pair in PAIRS for f in pair if os.path.exists(os.path.join(DOCS, f))]


def _strip_code(text: str) -> str:
    return re.sub(r"```.*?```", "", text, flags=re.S)


@pytest.mark.parametrize("zh,en", PAIRS)
def test_pairs_exist_together(zh, en):
    a, b = (os.path.exists(os.path.join(DOCS, f)) for f in (zh, en))
    if zh in PENDING and not (a or b):
        pytest.skip("GUI guide not written yet")
    assert a and b, f"{zh} / {en}: both languages must exist"


@pytest.mark.parametrize("zh,en", PAIRS)
def test_same_heading_structure(zh, en):
    if not all(os.path.exists(os.path.join(DOCS, f)) for f in (zh, en)):
        pytest.skip("pair incomplete")

    def levels(name):
        return [len(m) for m in re.findall(r"^(#{1,6}) ", _strip_code(_read(name)), flags=re.M)]
    assert levels(zh) == levels(en)


@pytest.mark.parametrize("name", _present())
def test_images_and_links(name):
    text = _strip_code(_read(name))
    for target in re.findall(r"!\[[^\]]*\]\(([^)\s]+)\)", text):
        assert os.path.exists(os.path.join(DOCS, target)), f"{name}: missing image {target}"
    for target in re.findall(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)", text):
        if re.match(r"https?://", target):
            continue
        path = target.split("#")[0]
        if not path or path in PENDING:
            continue
        assert os.path.exists(os.path.join(DOCS, path)), f"{name}: dead link {target}"


def _formulas(text: str) -> list[str]:
    text = _strip_code(text)
    display = re.findall(r"\$\$(.+?)\$\$", text, flags=re.S)
    inline = re.findall(r"(?<!\$)\$([^$\n]+?)\$(?!\$)", re.sub(r"\$\$.+?\$\$", "", text, flags=re.S))
    return [f.strip() for f in display + inline]


@pytest.mark.parametrize("name", _present())
def test_formulas_render(name):
    from matplotlib.mathtext import MathTextParser
    parser = MathTextParser("path")
    text = _read(name)
    assert text.count("$$") % 2 == 0, f"{name}: unbalanced $$"
    for f in _formulas(text):
        parser.parse(f"${f}$")            # raises ValueError on unsupported syntax


@pytest.mark.parametrize("name", _present())
def test_orbital_numbers_match_table(name):
    """Tables marked <!-- check: orbitals --> list level | BE | splitting | ratio as in data/orbitals.json."""
    text = _read(name)
    if "<!-- check: orbitals -->" not in text:
        return
    with open(ORBITALS, encoding="utf-8") as f:
        orb = json.load(f)["orbitals"]
    body = text.split("<!-- check: orbitals -->", 1)[1].strip().splitlines()[2:]   # skip header + rule
    end = next((i for i, r in enumerate(body) if not r.startswith("|")), len(body))
    rows = body[:end]
    assert len(rows) >= 3, f"{name}: orbital table not found under the marker"
    for r in rows:
        level, be, split, ratio = [c.strip() for c in r.strip("|").split("|")]
        o = orb[level]
        assert float(be) == pytest.approx(o["be"], abs=0.051), level
        assert float(split) == pytest.approx(o["split"], abs=0.0051), level
        assert float(ratio) == pytest.approx(o["ratio"], abs=0.00051), level


def test_text_is_utf8_without_bom():
    for name in _present():
        with open(os.path.join(DOCS, name), "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), name
        raw.decode("utf-8")
