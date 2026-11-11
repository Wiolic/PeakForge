"""Small helpers shared by the main window and its mixins."""
from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout

def _dot(color: str, d: int = 10) -> QIcon:
    pm = QPixmap(d * 2, d * 2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setBrush(QColor(color)); p.setPen(Qt.PenStyle.NoPen)
    p.drawEllipse(4, 4, d * 2 - 8, d * 2 - 8)
    p.end()
    return QIcon(pm)


def _card(title, margins=(12, 10, 12, 10)):
    f = QFrame(); f.setObjectName("card")
    lay = QVBoxLayout(f); lay.setContentsMargins(*margins); lay.setSpacing(8)
    if title:
        t = QLabel(title); t.setObjectName("cardTitle")
        if margins[0] == 0:
            t.setContentsMargins(14, 0, 14, 0)
        lay.addWidget(t)
    return f, lay


ICON = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "peakforge.ico")
