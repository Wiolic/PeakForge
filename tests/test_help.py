"""In-app help documents (src/peakforge/docs): zh/en pairs, structure, images, links, formulas, and the
numbers quoted from the orbital table; HelpWindow (gui/help.py) offscreen at the end."""
from __future__ import annotations

import json
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "src", "peakforge", "docs")
ORBITALS = os.path.join(ROOT, "src", "peakforge", "data", "orbitals.json")
sys.path.insert(0, os.path.join(ROOT, "src"))

PAIRS = [("XPS基础讲义.md", "XPS_basics_en.md"),
         ("零基础XPS拟合教程.md", "fitting_tutorial_en.md"),
         ("图形界面使用指南.md", "GUI_guide_en.md")]
PENDING: set[str] = set()      # documents that may not exist yet (links to them are allowed)


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
        pytest.skip("not written yet")
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


# ---- HelpWindow (offscreen) -------------------------------------------------------------------------------------
@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("lang", ["zh", "en"])
def test_help_window_pages_and_language(qapp, lang, monkeypatch):
    from peakforge.gui import help as H
    from peakforge.gui import i18n
    monkeypatch.setattr(i18n, "_lang", lang)
    w = H.HelpWindow()
    assert w.lang == lang
    for key in ("gui", "tutorial", "basics", "about"):
        w.show_tab(key)
        assert w.current_key() == key
    for key, r in w.readers.items():
        assert r.toPlainText().strip(), key
        assert os.path.exists(os.path.join(DOCS, H.doc_file(key, lang)))
    w.close()


def test_help_links_switch_pages(qapp):
    from PySide6.QtCore import QUrl
    from peakforge.gui import help as H
    w = H.HelpWindow()
    w.readers["tutorial"]._link(QUrl("XPS基础讲义.md"))
    assert w.current_key() == "basics"
    w.readers["basics"]._link(QUrl("GUI_guide_en.md"))
    assert w.current_key() == "gui"
    w.close()


def test_render_math_replaces_formulas_and_keeps_bad_ones(qapp):
    from peakforge.gui.help import render_math
    bs = chr(92)
    src = chr(10).join([f'a $E=h{bs}nu$ b', '', '$$x^2$$', '', '```', '$not$', '```', f'${bs}badcommand{{$'])
    md, d = render_math(src)
    assert md.count('![formula](') == 2 and '$not$' in md
    names = __import__('re').findall(r'[(](pf_math_[0-9a-f]+[.]png)[)]', md)
    assert len(names) == 2 and all((d / m).exists() for m in names)


def test_main_window_shows_single_help_window(qapp, tmp_path):
    from peakforge.gui.main_window import MainWindow
    w = MainWindow()
    w.show_help()
    first = w._help
    w.show_help("tutorial")
    assert w._help is first and first.current_key() == "tutorial"
    w.close()


def test_reader_images_are_hidpi_and_clickable(qapp):
    from PySide6.QtGui import QTextDocument
    from PySide6.QtCore import QPointF, QUrl
    from peakforge.gui import help as H
    w = H.HelpWindow()
    doc = w.readers["gui"].document()
    im = doc.resource(QTextDocument.ResourceType.ImageResource, QUrl("images/gui_main.png"))
    assert im is not None and not im.isNull()
    assert im.width() / im.devicePixelRatio() <= H.MAX_W + 1      # shown at most MAX_W wide, at screen resolution
    w.show()
    qapp.processEvents()
    r = w.readers["gui"]
    vw, vh = r.viewport().width(), r.viewport().height()
    r.verticalScrollBar().setValue(vh // 2)                   # hit test must account for scrolling
    hits = {r.figure_at(QPointF(x, y)) for x in range(10, vw, 40) for y in range(10, vh, 20)}
    assert "images/gui_main.png" in hits                           # a click there opens the full-size file
    w.close()


def test_reader_is_readable_and_font_adjustable(qapp, monkeypatch):
    from peakforge.gui import help as H
    from peakforge.gui import i18n
    saved = {}
    monkeypatch.setattr(i18n, "save_setting", lambda k, v: saved.__setitem__(k, v))   # never touch the real settings
    w = H.HelpWindow()
    r = w.readers["tutorial"]
    assert r.pt >= 13 and r.document().defaultFont().pointSizeF() >= 13
    heads, body = {}, []
    b = r.document().begin()
    while b.isValid():
        lvl = b.blockFormat().headingLevel()
        if lvl:
            heads.setdefault(lvl, b.charFormat().fontPointSize() or b.begin().fragment().charFormat().fontPointSize())
        if b.text().strip() and not lvl and b.blockFormat().lineHeight() >= 140:
            body.append(b.blockFormat().lineHeight())
        b = b.next()
    levels = sorted(heads)
    assert len(levels) >= 2 and all(heads[a] > heads[c] for a, c in zip(levels, levels[1:])), heads   # graded headings
    assert body and min(body) >= 140                                                                     # roomy lines
    before = r.pt
    w.change_font(1)
    assert all(x.pt == before + 1 for x in w.readers.values()) and saved["help_font"] == before + 1
    for _ in range(30):
        w.change_font(1)
    assert all(x.pt == H.FONT_MAX for x in w.readers.values())
    w.change_font(0)
    assert all(x.pt == H.FONT_PT for x in w.readers.values())
    w.close()
