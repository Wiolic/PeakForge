"""Figure themes shared by the matplotlib renderer and the Origin exporter.

'ir_blue' reproduces the user's Ir-new.opju template: Arial, hollow-circle data, dark-blue
background / envelope lines, light-blue filled components, no y tick labels, L-shaped frame.
"""
from __future__ import annotations

THEMES: dict[str, dict] = {
    "ir_blue": dict(
        name_en="Ir-new blue (default)", name_zh="Ir-new 蓝色系（默认）",
        data=(126, 170, 234), background=(38, 85, 123), envelope=(30, 95, 191),
        components=[(75, 136, 226), (142, 156, 255), (170, 199, 241), (197, 204, 254),
                    (98, 160, 210), (120, 120, 220), (185, 215, 250), (150, 175, 225)],
        fill_alpha=0.25, line_width=1.5, data_size=8, font="Arial"),
    "warm": dict(
        name_en="Warm", name_zh="暖色系",
        data=(150, 150, 150), background=(110, 60, 40), envelope=(200, 60, 30),
        components=[(230, 120, 60), (245, 170, 80), (210, 90, 110), (250, 205, 120),
                    (190, 110, 70), (240, 145, 145)],
        fill_alpha=0.3, line_width=1.5, data_size=8, font="Arial"),
    "contrast": dict(
        name_en="High contrast", name_zh="多色区分",
        data=(120, 120, 120), background=(90, 90, 90), envelope=(20, 20, 20),
        components=[(31, 119, 180), (255, 127, 14), (44, 160, 44), (148, 103, 189),
                    (214, 39, 40), (140, 86, 75), (227, 119, 194), (23, 190, 207)],
        fill_alpha=0.3, line_width=1.5, data_size=8, font="Arial"),
    "muted": dict(
        name_en="Muted journal", name_zh="低饱和期刊风",
        data=(140, 140, 140), background=(100, 100, 100), envelope=(40, 40, 40),
        components=[(68, 119, 170), (204, 102, 119), (34, 136, 51), (204, 187, 68),
                    (102, 204, 238), (170, 51, 119)],
        fill_alpha=0.35, line_width=1.5, data_size=8, font="Arial"),
    "gray": dict(
        name_en="Grayscale", name_zh="灰度",
        data=(110, 110, 110), background=(70, 70, 70), envelope=(0, 0, 0),
        components=[(90, 90, 90), (140, 140, 140), (180, 180, 180), (210, 210, 210),
                    (60, 60, 60), (160, 160, 160)],
        fill_alpha=0.35, line_width=1.5, data_size=8, font="Arial"),
}


def theme(name: str | None) -> dict:
    return THEMES.get(name or "ir_blue", THEMES["ir_blue"])


def rgb01(c):
    return tuple(v / 255 for v in c)


def comp_color(th: dict, i: int, override: str | None = None):
    if override:
        h = override.lstrip("#")
        return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))
    return th["components"][i % len(th["components"])]


def region_mathtext(region: str) -> str:
    """'Ir 4f' -> 'Ir 4$\\it{f}$' (italic orbital letter, as in the template)."""
    import re
    m = re.match(r"^([A-Z][a-z]?) (\d)([spdf])(.*)$", region)
    if not m:
        return region
    el, n, l, rest = m.groups()
    return f"{el} {n}$\\it{{{l}}}${rest}"


def region_origin(region: str) -> str:
    """Origin rich text: 'Ir 4\\i(f)'."""
    import re
    m = re.match(r"^([A-Z][a-z]?) (\d)([spdf])(.*)$", region)
    if not m:
        return region
    el, n, l, rest = m.groups()
    return f"{el} {n}\\i({l}){rest}"


_SUP = dict(zip("⁰¹²³⁴⁵⁶⁷⁸⁹⁺⁻⁼⁽⁾", "0123456789+-=()"))
_SUB = dict(zip("₀₁₂₃₄₅₆₇₈₉₊₋₌₍₎", "0123456789+-=()"))


def _runs(text: str):
    """Split into (kind, chunk) runs, kind in {'n', 'sup', 'sub'}."""
    out = []
    for ch in text:
        k = "sup" if ch in _SUP else "sub" if ch in _SUB else "n"
        c = _SUP.get(ch) or _SUB.get(ch) or ch
        if out and out[-1][0] == k:
            out[-1][1] += c
        else:
            out.append([k, c])
    return out


def label_mathtext(text: str) -> str:
    """'Ir⁴⁺' -> 'Ir$^{4+}$', 'H₂O' -> 'H$_{2}$O' (fonts like Arial lack the unicode glyphs)."""
    parts = []
    for k, c in _runs(text):
        c2 = c.replace("$", r"\$")
        parts.append(c2 if k == "n" else ("$^{%s}$" if k == "sup" else "$_{%s}$") % c)
    return "".join(parts)


def label_origin(text: str) -> str:
    r"""Origin rich text: superscript \+(..), subscript \-(..)."""
    parts = []
    for k, c in _runs(text):
        parts.append(c if k == "n" else (r"\+(%s)" if k == "sup" else r"\-(%s)") % c)
    return "".join(parts)
