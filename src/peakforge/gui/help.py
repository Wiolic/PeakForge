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
from PySide6.QtGui import QDesktopServices, QGuiApplication, QIcon, QImage, QTextDocument
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


class _Reader(QTextBrowser):
    """Markdown reader: links to the other bundled documents switch the page, http(s) links open the browser."""

    def __init__(self, win: "HelpWindow", size: float = 11.5):
        super().__init__()
        self.win = win
        self.setOpenLinks(False)
        self.anchorClicked.connect(self._link)
        f = self.document().defaultFont()
        f.setPointSizeF(size)
        self.document().setDefaultFont(f)
        self.setStyleSheet(f"QTextBrowser{{background:{C['card']};border:none;padding:6px 18px;}}")
        self.document().setDefaultStyleSheet(
            f"h1,h2,h3,h4{{color:{C['text']};}} a{{color:{C['accent_text']};}} td,th{{padding:4px 8px;}} li{{margin-bottom:4px;}}")

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
        md, mdir = render_math(md)
        self.setSearchPaths([str(DOCS), str(mdir)])
        self.setMarkdown(md)
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
        for key, tkey, ic, _zh, _en in DOC_SPECS:
            r = _Reader(self)
            r.load(doc_file(key, self.lang))
            self.readers[key] = r
            self._add(v, grp, key, tr(tkey), ic, r)
        v.addStretch(1)
        self._add(v, grp, "about", tr("help_about"), "bot", self._about())
        h.addWidget(side)
        h.addWidget(self.stack, 1)
        self.setCentralWidget(root)
        self.show_tab("gui")

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
