"""Light minimal look: colour tokens, Qt style sheet, line icons, matplotlib styling."""
from __future__ import annotations

from PySide6.QtCore import QByteArray, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

C = dict(
    window="#F5F6F8", card="#FFFFFF", border="#E4E6EB", border_strong="#D3D6DD",
    text="#1F2329", muted="#6B7280", faint="#9AA1AC",
    accent="#2F6BDF", accent_hover="#255BC4", accent_soft="#EAF1FD", accent_text="#1D4FB8",
    hover="#F1F3F6", danger="#D14343", ok="#2E8B57", warn="#B7791F",
)
import os as _os
_A = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "assets").replace("\\", "/")
FONT_UI = '"Microsoft YaHei UI", "Segoe UI", "PingFang SC", sans-serif'

QSS = f"""
* {{ font-family: {FONT_UI}; font-size: 9.5pt; color: {C['text']}; }}
QMainWindow, QWidget#root {{ background: {C['window']}; }}
QMenuBar {{ background: {C['card']}; border-bottom: 1px solid {C['border']}; padding: 2px 6px; }}
QMenuBar::item {{ padding: 5px 10px; border-radius: 6px; background: transparent; }}
QMenuBar::item:selected {{ background: {C['hover']}; }}
QMenu {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 22px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {C['accent_soft']}; color: {C['accent_text']}; }}
QMenu::item:disabled {{ color: {C['faint']}; }}
QMenu::separator {{ height: 1px; background: {C['border']}; margin: 5px 8px; }}

QFrame#topbar {{ background: {C['card']}; border-bottom: 1px solid {C['border']}; }}
QLabel#brand {{ font-size: 11.5pt; font-weight: 600; }}
QLabel#credit {{ color: {C['accent_text']}; font-size: 8pt; font-weight: 600; }}
QLabel#brandSub {{ color: {C['muted']}; }}
QFrame#card {{ background: {C['card']}; border: 1px solid {C['border']}; border-radius: 10px; }}
QLabel#cardTitle {{ font-weight: 600; font-size: 10pt; }}
QLabel#sectionTitle {{ color: {C['muted']}; font-size: 8.5pt; font-weight: 600; letter-spacing: 0.5px; }}
QLabel#hint {{ color: {C['muted']}; font-size: 8.5pt; }}
QLabel#metric {{ color: {C['muted']}; }}

QToolButton {{ border: none; border-radius: 7px; padding: 5px 9px; background: transparent; }}
QToolButton:hover {{ background: {C['hover']}; }}
QToolButton:pressed, QToolButton:checked {{ background: {C['accent_soft']}; color: {C['accent_text']}; }}
QToolButton#primaryTool {{ background: {C['accent']}; color: white; padding: 5px 12px; }}
QToolButton#primaryTool:hover {{ background: {C['accent_hover']}; }}

QPushButton {{ background: {C['card']}; border: 1px solid {C['border_strong']}; border-radius: 7px;
               padding: 5px 12px; }}
QPushButton:hover {{ background: {C['hover']}; }}
QPushButton:disabled {{ color: {C['faint']}; border-color: {C['border']}; }}
QPushButton#primary {{ background: {C['accent']}; color: white; border: 1px solid {C['accent']}; font-weight: 600;
                       padding: 6px 18px; }}
QPushButton#primary:hover {{ background: {C['accent_hover']}; }}
QPushButton#primary:disabled {{ background: #A9C0EE; border-color: #A9C0EE; }}
QPushButton#ghost {{ border: none; color: {C['accent_text']}; padding: 4px 8px; }}
QPushButton#ghost:hover {{ background: {C['accent_soft']}; }}

QComboBox, QLineEdit, QDoubleSpinBox, QSpinBox {{ background: {C['card']}; border: 1px solid {C['border_strong']};
    border-radius: 7px; padding: 4px 8px; min-height: 20px; selection-background-color: {C['accent_soft']};
    selection-color: {C['accent_text']}; }}
QComboBox:hover, QLineEdit:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: #B9BEC8; }}
QComboBox:focus, QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{ border: 1px solid {C['border']}; border-radius: 8px; padding: 4px; outline: 0;
    background: {C['card']}; }}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button, QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}

QTreeWidget, QTableWidget, QListWidget, QPlainTextEdit {{ background: {C['card']}; border: none; outline: 0;
    alternate-background-color: #FAFBFC; }}
QTreeWidget::item, QListWidget::item {{ padding: 4px 4px; border-radius: 6px; }}
QTreeWidget::item:hover, QListWidget::item:hover {{ background: {C['hover']}; }}
QTreeWidget::item:selected, QListWidget::item:selected {{ background: {C['accent_soft']}; color: {C['accent_text']}; }}
QTreeWidget::branch {{ background: transparent; }}
QTableWidget {{ gridline-color: {C['border']}; }}
QTableWidget::item {{ padding: 2px 6px; }}
QTableWidget::item:selected {{ background: {C['accent_soft']}; color: {C['accent_text']}; }}
QHeaderView::section {{ background: {C['card']}; color: {C['muted']}; border: none;
    border-bottom: 1px solid {C['border']}; padding: 5px 6px; font-size: 8.5pt; font-weight: 600; }}
QHeaderView {{ background: {C['card']}; border: none; }}
QTableCornerButton::section {{ background: {C['card']}; border: none; }}
QPlainTextEdit {{ font-family: "Cascadia Mono", Consolas, monospace; font-size: 9pt; padding: 6px; }}

QTabWidget::pane {{ border: none; border-top: 1px solid {C['border']}; }}
QTabBar::tab {{ background: transparent; border: none; padding: 7px 14px; color: {C['muted']};
    border-bottom: 2px solid transparent; }}
QTabBar::tab:selected {{ color: {C['text']}; border-bottom: 2px solid {C['accent']}; font-weight: 600; }}
QTabBar::tab:hover {{ color: {C['text']}; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 8px; }}
QSplitter::handle:vertical {{ height: 8px; }}
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ width: 9px; background: transparent; margin: 2px; }}
QScrollBar:horizontal {{ height: 9px; background: transparent; margin: 2px; }}
QScrollBar::handle {{ background: #CDD1D8; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background: #B3B8C1; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ height: 0; width: 0; background: none; }}
QCheckBox::indicator, QTableWidget::indicator, QTreeWidget::indicator, QListWidget::indicator {{
    width: 15px; height: 15px; image: url("{_A}/uncheck.svg"); }}
QCheckBox::indicator:checked, QTableWidget::indicator:checked, QTreeWidget::indicator:checked,
QListWidget::indicator:checked {{ image: url("{_A}/check.svg"); }}
QWidget#modelPanel {{ background: transparent; }}
QStatusBar {{ background: {C['card']}; border-top: 1px solid {C['border']}; color: {C['muted']}; }}
QStatusBar QLabel {{ color: {C['muted']}; }}
QToolTip {{ background: #1F2329; color: white; border: none; border-radius: 6px; padding: 5px 8px; }}
QDialog {{ background: {C['window']}; }}
QGroupBox {{ border: none; margin-top: 18px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 0; padding: 0; color: {C['muted']}; font-size: 8.5pt; }}
"""

# 24x24 line icons (stroke-based, Lucide-style geometry drawn for this app)
_ICONS = {
    "folder": '<path d="M3 7.5a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2V17a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>',
    "import": '<path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z"/><path d="M14 3v5h5"/>'
              '<path d="M12 11v6"/><path d="M9 14l3 3 3-3"/>',
    "target": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="2.5"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/>',
    "play": '<path d="M7 4.5v15l12-7.5z"/>',
    "layers": '<path d="M12 3 3 7.5l9 4.5 9-4.5z"/><path d="M3 12l9 4.5 9-4.5"/><path d="M3 16.5 12 21l9-4.5"/>',
    "pulse": '<path d="M3 12h4l3-7 4 14 3-7h4"/>',
    "export": '<path d="M12 3v12"/><path d="M7 8l5-5 5 5"/><path d="M5 14v5a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-5"/>',
    "home": '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h5v-6h4v6h5V10"/>',
    "move": '<path d="M12 3v18M3 12h18"/><path d="M9 6l3-3 3 3M9 18l3 3 3-3M6 9l-3 3 3 3M18 9l3 3-3 3"/>',
    "zoom": '<circle cx="11" cy="11" r="6.5"/><path d="M20.5 20.5 16 16"/><path d="M11 8.5v5M8.5 11h5"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="1.8"/><path d="M21 16l-5-5-9 9"/>',
    "undo": '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>',
    "redo": '<path d="M15 14l5-5-5-5"/><path d="M20 9H10a6 6 0 0 0 0 12h3"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "trash": '<path d="M4 7h16"/><path d="M9 7V4h6v3"/><path d="M6 7l1 13h10l1-13"/>',
    "palette": '<path d="M12 3a9 9 0 1 0 0 18c1.2 0 1.8-.8 1.8-1.7 0-1.4-1.3-1.6-1.3-2.8 0-1 .8-1.6 1.8-1.6H17a4 4 0 0 0 4-4c0-4.4-4-7.9-9-7.9z"/>'
               '<circle cx="7.5" cy="11" r="1"/><circle cx="10" cy="7" r="1"/><circle cx="15" cy="7.5" r="1"/>',
    "bot": '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 4v4"/><circle cx="12" cy="3.5" r="1"/>'
           '<path d="M9 13v1.5M15 13v1.5"/><path d="M2 13v3M22 13v3"/>',
    "flask": '<path d="M9 3h6"/><path d="M10 3v6L4.5 18.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3"/><path d="M7.5 15h9"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/>'
               '<circle cx="10" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "percent": '<path d="M19 5 5 19"/><circle cx="7" cy="7" r="2.5"/><circle cx="17" cy="17" r="2.5"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V6a2 2 0 0 0-2-2H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h2"/>',
}


def icon(name: str, color: str | None = None, size: int = 18) -> QIcon:
    col = color or C["text"]
    body = _ICONS.get(name, "")
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{col}" '
           f'stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    r = QSvgRenderer(QByteArray(svg.encode()))
    ic = QIcon()
    for s in (size, size * 2):
        pm = QPixmap(s, s)
        pm.fill(Qt.GlobalColor.transparent)
        p = QPainter(pm)
        r.render(p, QRectF(0, 0, s, s))
        p.end()
        ic.addPixmap(pm)
    return ic


def swatch(colors, w: int = 84, h: int = 14) -> QIcon:
    """Horizontal strip of colour blocks (for the palette picker)."""
    pm = QPixmap(w * 2, h * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    n = len(colors)
    bw = pm.width() / n
    for i, c in enumerate(colors):
        p.setBrush(QColor(*c))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRect(QRectF(i * bw, 0, bw + 0.5, pm.height()))
    p.end()
    ic = QIcon(pm)
    return ic


SWATCH_SIZE = QSize(84, 14)


def mpl_style():
    import matplotlib
    rc = matplotlib.rcParams
    rc["font.family"] = ["Segoe UI", "Microsoft YaHei", "Arial", "DejaVu Sans"]
    rc["font.size"] = 9
    rc["axes.unicode_minus"] = False
    rc["axes.edgecolor"] = "#9AA1AC"
    rc["axes.labelcolor"] = C["muted"]
    rc["xtick.color"] = "#8A919C"
    rc["ytick.color"] = "#8A919C"
    rc["xtick.labelcolor"] = C["muted"]
    rc["axes.linewidth"] = 0.9
    rc["axes.titlesize"] = 10
    rc["axes.titleweight"] = "semibold"
    rc["axes.titlecolor"] = C["text"]
    rc["legend.labelcolor"] = C["text"]
