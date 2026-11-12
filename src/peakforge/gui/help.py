"""Help window: a separate, non-modal window (can sit beside the main window) with the three bundled documents
(GUI guide, fitting tutorial for beginners, XPS basics) and an About page (version, credit, disclaimer, logs).

Documents live in ``peakforge/docs`` (zh / en pairs, chosen by the UI language). Formulas (``$...$`` / ``$$...$$``)
are rendered to PNG with matplotlib mathtext (Figure + Agg, never pyplot) and cached in the temp folder.

All images (``docs/images`` and formulas) are stored at ``IMG_SCALE`` x their display size. The reader shrinks them
once, smoothly, to the screen's device pixels and tags them with its pixel ratio, so they stay sharp on high-DPI
screens (Qt itself would stretch a 1x image or shrink a wide one without smoothing)."""
from __future__ import annotations

import hashlib
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import QPointF, QSize, Qt, QUrl
from PySide6.QtGui import (QBrush, QColor, QDesktopServices, QGuiApplication, QIcon, QImage, QKeySequence,
                           QShortcut, QTextBlockFormat, QTextCharFormat, QTextCursor, QTextDocument, QTextFrame,
                           QTextLength, QTextTable)
from PySide6.QtWidgets import (QButtonGroup, QHBoxLayout, QLabel, QMainWindow, QPushButton, QStackedWidget, QTextBrowser,
                               QVBoxLayout, QWidget)

from .. import APP_NAME, CREDIT, DISCLAIMER_EN, DISCLAIMER_ZH, __version__
from ..logs import log
from . import i18n
from .i18n import tr
from .style import C, icon

DOCS = Path(__file__).resolve().parent.parent / "docs"
ASSETS = Path(__file__).resolve().parent.parent / "assets"
REPO = "https://github.com/Wiolic/PeakForge"
IMG_SCALE = 2          # docs/images/*.png and formula images are rendered at 2x their display size
MAX_W = 720            # widest image in the reader (logical pixels)
TEXT_W = 800           # widest text column (logical pixels); the page is centred when the window is wider
FONT_PT, FONT_MIN, FONT_MAX = 13.0, 10.0, 20.0   # reading size (adjustable with Ctrl+wheel / Ctrl+ +/-/0, remembered)

# key, i18n key of the title, icon, zh file, en file
DOC_SPECS = [
    ("gui", "help_gui", "sliders", "图形界面使用指南.md", "GUI_guide_en.md"),
    ("tutorial", "help_tutorial", "flask", "零基础XPS拟合教程.md", "fitting_tutorial_en.md"),
    ("basics", "help_basics", "target", "XPS基础讲义.md", "XPS_basics_en.md"),
]


def doc_file(key: str, lang: str | None = None) -> str:
    """File name of a document in the given (default: current) UI language."""
    en = (lang or i18n.lang()) == "en"
    for k, _t, _i, zh, e in DOC_SPECS:
        if k == key:
            return e if en else zh
    raise KeyError(key)


def _tex(s: str) -> str:
    """LaTeX as written in the Markdown -> what matplotlib mathtext understands."""
    s = s.replace("\\!", "").replace("\\text{", "\\mathrm{").replace("\\left", "").replace("\\right", "")
    s = s.replace("\\|", "|")
    return re.sub(r"\\(?:,|;|quad)", " ", s)


def render_math(md: str, size: float = 14, color: str | None = None) -> tuple[str, Path]:
    """Replace ``$$...$$`` (display) and ``$...$`` (inline) by image references to PNGs rendered with matplotlib
    mathtext. One image per formula and colour (cached by content hash in the temp folder). A formula that cannot
    be rendered stays as text (and is logged). Returns (markdown, folder with the images)."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure
    d = Path(tempfile.gettempdir()) / "peakforge_math"
    d.mkdir(parents=True, exist_ok=True)
    col = color or C["text"]

    def img(tex: str, display: bool) -> str | None:
        key = hashlib.md5(f"v2|{tex}|{display}|{col}|{size}".encode("utf-8")).hexdigest()[:16]
        f = d / f"pf_math_{key}.png"
        if not f.exists():
            try:
                fig = Figure()
                FigureCanvasAgg(fig)
                fig.text(0, 0, f"${_tex(tex)}$", fontsize=size * (1.3 if display else 1.0), color=col)
                fig.savefig(str(f), dpi=96 * 1.05 * IMG_SCALE, transparent=True, bbox_inches="tight", pad_inches=0.02, format="png")
            except (ValueError, RuntimeError, OSError) as e:
                log.warning("help: formula not rendered (%s): %s", tex[:60], e)
                return None
        return f.name

    def disp(m: re.Match) -> str:
        n = img(m.group(1).strip(), True)
        return f"\n\n![formula]({n})\n\n" if n else m.group(0)       # an empty alt text is dropped by Qt

    def inline(m: re.Match) -> str:
        n = img(m.group(1), False)
        return f"![formula]({n})" if n else m.group(0)

    # code blocks are left alone
    parts = re.split(r"(```.*?```)", md, flags=re.S)
    for i in range(0, len(parts), 2):
        t = re.sub(r"\$\$(.+?)\$\$", disp, parts[i], flags=re.S)
        parts[i] = re.sub(r"(?<![\\$])\$([^$\n]+?)\$", inline, t)
    return "".join(parts), d


def reader_css(pt: float) -> str:
    """Default style sheet of the reader: sizes scale with the base size ``pt`` (Qt rich text has no rem/em)."""
    t, m, ac = C["text"], C["muted"], C["accent_text"]
    return (
        f"body{{color:{t};}}"
        f"p{{margin-top:6px;margin-bottom:10px;line-height:165%;}}"
        f"li{{margin-top:3px;margin-bottom:5px;line-height:160%;}}"
        f"h1{{font-size:{pt * 2.0:.1f}pt;font-weight:700;color:{t};margin-top:6px;margin-bottom:14px;}}"
        f"h2{{font-size:{pt * 1.55:.1f}pt;font-weight:700;color:{ac};margin-top:34px;margin-bottom:12px;}}"
        f"h3{{font-size:{pt * 1.25:.1f}pt;font-weight:700;color:{t};margin-top:24px;margin-bottom:8px;}}"
        f"h4{{font-size:{pt * 1.08:.1f}pt;font-weight:700;color:{m};margin-top:18px;margin-bottom:6px;}}"
        f"a{{color:{ac};}}"
        f"code{{font-family:Consolas,'Cascadia Mono',monospace;background-color:{C['hover']};color:{t};}}"
        f"pre{{font-family:Consolas,'Cascadia Mono',monospace;background-color:{C['hover']};margin-top:8px;margin-bottom:12px;}}"
        f"blockquote{{color:{m};background-color:{C['accent_soft']};margin-top:10px;margin-bottom:14px;}}"
        f"th{{font-weight:700;}}"
    )


class _Reader(QTextBrowser):
    """Markdown reader: links to the other bundled documents switch the page, http(s) links open the browser.
    Readable by default: 13 pt text, 155 % line spacing, clearly graded headings, a column of at most TEXT_W."""

    def __init__(self, win: "HelpWindow", size: float = FONT_PT):
        super().__init__()
        self.win = win
        self.fname = ""
        self.pt = size
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._link)
        self.document().setDocumentMargin(4)
        self._apply_font()

    def _apply_font(self) -> None:
        # the app style sheet sets 9.5 pt on every widget, so the size must come from the widget's own style sheet
        self.setStyleSheet(f"QTextBrowser{{background:{C['card']};border:none;font-size:{self.pt:g}pt;}}")
        f = self.document().defaultFont()
        f.setPointSizeF(self.pt)
        self.document().setDefaultFont(f)
        self.document().setDefaultStyleSheet(reader_css(self.pt))

    def set_size(self, pt: float) -> None:
        """Change the reading size and re-render the page (keeps the scroll position)."""
        pt = max(FONT_MIN, min(FONT_MAX, round(pt * 2) / 2))
        if pt == self.pt or not self.fname:
            return
        bar = self.verticalScrollBar()
        frac = bar.value() / max(1, bar.maximum())
        self.pt = pt
        self._apply_font()
        self.load(self.fname)
        bar.setValue(round(frac * bar.maximum()))

    def wheelEvent(self, e) -> None:              # noqa: ANN001
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.win.change_font(1 if e.angleDelta().y() > 0 else -1)
            e.accept()
            return
        super().wheelEvent(e)

    def resizeEvent(self, e) -> None:             # noqa: ANN001
        m = max(24, (self.width() - TEXT_W) // 2)     # centre the text column, 24 px minimum gutter
        self.setViewportMargins(m, 8, m, 16)
        super().resizeEvent(e)                        # after the margins: the document is laid out for the column

    def _style_blocks(self) -> None:
        """Qt's Markdown import ignores style sheets: grade the headings and set line / paragraph spacing by hand."""
        pt = self.pt
        heading = {1: (2.0, 4, 16, C["text"]), 2: (1.55, 34, 12, C["accent_text"]),
                   3: (1.25, 24, 8, C["text"]), 4: (1.08, 18, 6, C["muted"])}
        doc = self.document()
        doc.setUndoRedoEnabled(False)
        block = doc.begin()
        while block.isValid():
            bf = block.blockFormat()
            nb = QTextBlockFormat(bf)
            cur = QTextCursor(block)
            lvl = bf.headingLevel()
            in_table = cur.currentTable() is not None
            if lvl in heading:
                k, top, bottom, col = heading[lvl]
                nb.setTopMargin(top)
                nb.setBottomMargin(bottom)
                nb.setLineHeight(120, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
                cf = QTextCharFormat()
                cf.setFontPointSize(pt * k)
                cf.setFontWeight(700)
                cf.setForeground(QBrush(QColor(col)))
                cur.select(QTextCursor.SelectionType.BlockUnderCursor)
                cur.mergeCharFormat(cf)
            elif in_table:
                nb.setLineHeight(145, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            elif block.textList() is not None:
                nb.setTopMargin(2)
                nb.setBottomMargin(6)
                nb.setLineHeight(150, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            else:
                nb.setTopMargin(4)
                nb.setBottomMargin(10)
                nb.setLineHeight(155, QTextBlockFormat.LineHeightTypes.ProportionalHeight.value)
            QTextCursor(block).setBlockFormat(nb)
            block = block.next()

    def _style_tables(self) -> None:
        """Qt's Markdown tables are bare: add padding, light borders and a shaded header row."""
        border = QBrush(QColor(C["border_strong"]))
        head = QColor(C["accent_soft"])

        def walk(frame: QTextFrame) -> None:
            for ch in frame.childFrames():
                if isinstance(ch, QTextTable):
                    fmt = ch.format()
                    fmt.setBorder(1)
                    fmt.setBorderBrush(border)
                    fmt.setCellPadding(8)
                    fmt.setCellSpacing(0)
                    fmt.setTopMargin(8)
                    fmt.setBottomMargin(14)
                    fmt.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
                    ch.setFormat(fmt)
                    for c in range(ch.columns()):
                        cell = ch.cellAt(0, c)
                        cf = cell.format().toTableCellFormat()
                        cf.setBackground(head)
                        cell.setFormat(cf)
                walk(ch)
        walk(self.document().rootFrame())

    def figure_at(self, pos: QPointF) -> str | None:
        """docs/images file under a viewport position (formulas excluded), else None."""
        p = QPointF(pos.x() + self.horizontalScrollBar().value(), pos.y() + self.verticalScrollBar().value())
        name = self.document().documentLayout().imageAt(p)
        return name if name.startswith("images/") and (DOCS / name).exists() else None

    def mouseMoveEvent(self, e) -> None:          # noqa: ANN001  (Qt event)
        super().mouseMoveEvent(e)
        if not self.anchorAt(e.position().toPoint()):
            hand = self.figure_at(e.position()) is not None
            self.viewport().setCursor(Qt.CursorShape.PointingHandCursor if hand else Qt.CursorShape.IBeamCursor)

    def mouseReleaseEvent(self, e) -> None:       # noqa: ANN001
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton and not self.textCursor().hasSelection():
            name = self.figure_at(e.position())
            if name:                              # a figure: open the full-resolution file in the image viewer
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(DOCS / name)))

    def _link(self, url: QUrl) -> None:
        s = url.toString()
        if url.scheme() in ("http", "https"):
            QDesktopServices.openUrl(url)
            return
        name = s.split("#")[0]
        for key, _t, _i, zh, en in DOC_SPECS:
            if name in (zh, en):
                self.win.show_tab(key)
                return
        if url.scheme() == "" and s.startswith("#"):
            self.scrollToAnchor(s[1:])

    def load(self, fname: str) -> None:
        p = DOCS / fname
        try:
            md = p.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("help: cannot read %s: %s", p, e)
            md = f"{fname}\n\n({e})"
        self.fname = fname
        md, mdir = render_math(md, size=14 * self.pt / FONT_PT)
        self.setSearchPaths([str(DOCS), str(mdir)])
        self.setMarkdown(md)
        self._style_blocks()
        self._style_tables()
        self._sharp_images([DOCS, mdir])


class HelpWindow(QMainWindow):
    """Non-modal help; the main window keeps one instance and brings it to the front on F1."""

    def __init__(self, main: QWidget | None = None):
        super().__init__()
        self.main = main
        self.lang = i18n.lang()
        self.setWindowTitle(f"{APP_NAME} — {tr('help_title')}")
        if (ASSETS / "peakforge.ico").exists():
            self.setWindowIcon(QIcon(str(ASSETS / "peakforge.ico")))
        self.setMinimumSize(760, 540)
        self.resize(1000, 760)
        root = QWidget()
        root.setObjectName("root")
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        side = QWidget()
        side.setFixedWidth(220)
        side.setStyleSheet(f"background:{C['window']};")
        v = QVBoxLayout(side)
        v.setContentsMargins(12, 16, 12, 14)
        v.setSpacing(3)
        t = QLabel(tr("help_title"))
        t.setObjectName("brand")
        v.addWidget(t)
        v.addSpacing(10)
        self.stack = QStackedWidget()
        self.btn: dict[str, tuple[QPushButton, QWidget]] = {}
        self.readers: dict[str, _Reader] = {}
        grp = QButtonGroup(self)
        pt = i18n.settings().get("help_font", FONT_PT)
        pt = float(pt) if isinstance(pt, (int, float)) else FONT_PT
        for key, tkey, ic, _zh, _en in DOC_SPECS:
            r = _Reader(self, max(FONT_MIN, min(FONT_MAX, pt)))
            r.load(doc_file(key, self.lang))
            self.readers[key] = r
            self._add(v, grp, key, tr(tkey), ic, r)
        v.addStretch(1)
        self._add(v, grp, "about", tr("help_about"), "bot", self._about())
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.show_tab("gui")
        for keys, step in (("Ctrl++", 1), ("Ctrl+=", 1), ("Ctrl+-", -1)):
            QShortcut(QKeySequence(keys), self, activated=lambda st=step: self.change_font(st))
        QShortcut(QKeySequence("Ctrl+0"), self, activated=lambda: self.change_font(0))

    def change_font(self, step: int) -> None:
        """Ctrl+wheel / Ctrl +,-: bigger or smaller text in all documents (0 = default); remembered."""
        cur = next(iter(self.readers.values())).pt
        new = FONT_PT if step == 0 else cur + 1 * step
        new = max(FONT_MIN, min(FONT_MAX, new))
        for r in self.readers.values():
            r.set_size(new)
        i18n.save_setting("help_font", new)

    def _add(self, v: QVBoxLayout, grp: QButtonGroup, key: str, title: str, ic: str, page: QWidget) -> None:
        b = QPushButton("  " + title.replace("&", "&&"))
        b.setCheckable(True)
        b.setIcon(icon(ic, C["muted"], 16))
        b.setIconSize(QSize(16, 16))
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setStyleSheet("QPushButton{text-align:left;border:none;padding:8px 10px;}"
                        f"QPushButton:checked{{background:{C['accent_soft']};color:{C['accent_text']};}}")
        b.clicked.connect(lambda _=False, k=key: self.show_tab(k))
        grp.addButton(b)
        v.addWidget(b)
        self.btn[key] = (b, page)
        self.stack.addWidget(page)

    def show_tab(self, key: str) -> None:
        """Switch to a page: gui / tutorial / basics / about (a dialog's "?" can jump to its chapter)."""
        if key in self.btn:
            b, page = self.btn[key]
            b.setChecked(True)
            self.stack.setCurrentWidget(page)

    def current_key(self) -> str:
        w = self.stack.currentWidget()
        return next((k for k, (_b, p) in self.btn.items() if p is w), "gui")

    def _about(self) -> QWidget:
        from .. import logs
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setStyleSheet(f"QTextBrowser{{background:{C['card']};border:none;padding:10px 22px;}}")
        zh = i18n.lang() == "zh"
        disc = DISCLAIMER_ZH if zh else DISCLAIMER_EN
        diag = ("出错时用“帮助 → 导出诊断包…”生成诊断包（日志、版本环境、工程与模型 JSON，不含原始数据与谱图数值）发给开发者。日志文件："
                if zh else "On errors use Help → Export diagnostics bundle… (log, environment, project and model JSON; "
                           "no raw data or spectra) and send it to the developer. Log file: ")
        tb.setHtml(
            f"<h2>{APP_NAME} {__version__}</h2>"
            f"<p><b style='color:{C['accent_text']}'>{CREDIT}</b> (Anthropic)</p>"
            "<p>XPS: SPE / VAMAS / CSV / Excel · constrained peak fitting for Li–U · diagnostics · Origin export · MCP.</p>"
            f"<h3>{tr('disclaimer')}</h3><p>{disc}</p>"
            f"<h3>{tr('help_diag')}</h3><p>{diag}<code>{logs.LOG_FILE}</code></p>"
            f"<p>MIT License · <a href='{REPO}'>{REPO}</a></p>")
        return tb


def _sharp_images(self: _Reader, search: list[Path]) -> None:
    """Replace every image of the document by a copy scaled smoothly to its display size in device pixels
    (display size = stored size / IMG_SCALE, at most MAX_W wide) and tagged with the screen's pixel ratio."""
    screen = self.screen() or QGuiApplication.primaryScreen()
    dpr = screen.devicePixelRatio() if screen else 1.0
    doc = self.document()
    names = set()
    block = doc.begin()
    while block.isValid():
        it = block.begin()
        while not it.atEnd():
            fmt = it.fragment().charFormat()
            if fmt.isImageFormat():
                names.add(fmt.toImageFormat().name())
            it += 1
        block = block.next()
    for name in names:
        f = next((d / name for d in search if (d / name).exists()), None)
        im = QImage(str(f)) if f else QImage()
        if im.isNull():
            log.warning("help: image not found: %s", name)
            continue
        w = min(im.width() / IMG_SCALE, MAX_W)
        h = im.height() * w / im.width()
        im = im.scaled(round(w * dpr), round(h * dpr), Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
        im.setDevicePixelRatio(dpr)
        doc.addResource(QTextDocument.ResourceType.ImageResource, QUrl(name), im)
    doc.markContentsDirty(0, doc.characterCount())


_Reader._sharp_images = _sharp_images
