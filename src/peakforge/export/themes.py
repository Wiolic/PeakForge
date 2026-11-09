"""Figure colour themes, shared by the matplotlib renderer, the GUI and the Origin exporter.

Naming system: every theme is a landscape, grouped into six families.

    family        themes (id: 中文 English)
    waters  水域   glacier 冰川 · fjord 峡湾 · lagoon 泻湖 · abyss 深海
    forests 森林   moss 苔原 · pinewood 松林 · bamboo 竹林 · rainforest 雨林
    earth   大地   desert 沙漠 · canyon 峡谷 · loess 黄土 · badlands 恶地
    skies   天穹   dawn 晨曦 · dusk 暮色 · aurora 极光 · twilight 薄暮
    stone   山岩   basalt 玄武 · granite 花岗 · slate 板岩 · highland 高地
    fields  原野   lavender 薰衣草田 · meadow 草甸 · autumn 秋野 · prairie 草原

kind  'mono'  one hue, light to dark (oxidation-state series read as one family)
      'poly'  clearly distinct hues (many unrelated components)
      'soft'  low-saturation mixed hues (journal / print friendly)
      'cvd'   colour-vision-deficiency safe (Okabe-Ito)

'glacier' (default) is the palette of the original Ir-new.opju template.
User themes: JSON files in ~/.peakforge/themes/ (see save_user_theme), family 'custom'.
"""
from __future__ import annotations

import json
import os
import re

FAMILIES = [
    ("waters", "水域", "Waters"), ("forests", "森林", "Forests"), ("earth", "大地", "Earth"),
    ("skies", "天穹", "Skies"), ("stone", "山岩", "Stone"), ("fields", "原野", "Fields"),
    ("custom", "自定义", "Custom"),
]
KINDS = {"mono": ("单色渐变", "monochrome"), "poly": ("多色对比", "contrast"),
         "soft": ("柔和期刊", "soft"), "cvd": ("色盲友好", "colour-blind safe")}
DEFAULT = "glacier"
ALIASES = {"ir_blue": "glacier", "warm": "canyon", "contrast": "rainforest", "muted": "highland",
           "gray": "basalt"}
USER_DIR = os.path.join(os.path.expanduser("~"), ".peakforge", "themes")


def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(c) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in c)


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _ramp(stops: list[str], n: int) -> list[tuple]:
    cs = [_hex(h) for h in stops]
    out = []
    for k in range(n):
        u = k / (n - 1) * (len(cs) - 1)
        i = min(int(u), len(cs) - 2)
        out.append(_mix(cs[i], cs[i + 1], u - i))
    return out


def _mono(stops):
    """8 component colours from a dark-to-light ramp, interleaved so neighbours contrast."""
    r = _ramp(stops[1:], 8)
    order = [0, 4, 2, 6, 1, 5, 3, 7]
    return dict(components=[r[i] for i in order], data=_mix(_hex(stops[3]), (255, 255, 255), 0.15),
                envelope=_hex(stops[1]), background=_mix(_hex(stops[0]), (90, 90, 90), 0.35),
                fill_alpha=0.32)


def _poly(colors, data="#8E9196", env="#2B2D31", bg="#6B6E73", alpha=0.30):
    return dict(components=[_hex(c) for c in colors], data=_hex(data), envelope=_hex(env),
                background=_hex(bg), fill_alpha=alpha)


def _t(family, kind, zh, en, spec):
    d = dict(family=family, kind=kind, name_zh=zh, name_en=en, line_width=1.5, data_size=8, font="Arial")
    d.update(spec)
    return d


THEMES: dict[str, dict] = {
    # waters 水域
    "glacier": _t("waters", "mono", "冰川", "Glacier", dict(
        data=(126, 170, 234), background=(38, 85, 123), envelope=(30, 95, 191),
        components=[(75, 136, 226), (142, 156, 255), (170, 199, 241), (197, 204, 254),
                    (98, 160, 210), (120, 120, 220), (185, 215, 250), (150, 175, 225)],
        fill_alpha=0.25)),
    "fjord": _t("waters", "mono", "峡湾", "Fjord",
                _mono(["#0F3D56", "#1F5673", "#2E6F8E", "#5FA3BF", "#A9D3E2", "#DCEFF5"])),
    "lagoon": _t("waters", "mono", "泻湖", "Lagoon",
                 _mono(["#0B4F4C", "#126B67", "#2A9D8F", "#76C7B7", "#B8E3D6", "#E3F4EE"])),
    "abyss": _t("waters", "mono", "深海", "Abyss",
                _mono(["#141E46", "#22306A", "#3B4E92", "#6878B8", "#A3AEDB", "#D6DBF1"])),
    # forests 森林
    "moss": _t("forests", "mono", "苔原", "Moss",
               _mono(["#2E3820", "#4A5A30", "#6B7D45", "#9AAA68", "#C6D09A", "#E6EBCF"])),
    "pinewood": _t("forests", "mono", "松林", "Pinewood",
                   _mono(["#16301F", "#244A33", "#3A6B4F", "#6E9C80", "#A8C8B3", "#DCEBE1"])),
    "bamboo": _t("forests", "soft", "竹林", "Bamboo", _poly(
        ["#4E8B57", "#A8C686", "#2F6B6B", "#D9C77A", "#7FA7A0", "#6B7F3A", "#C4D9B0", "#8C6F4E"],
        data="#8FA596", env="#1F3A2B", bg="#5F6F63")),
    "rainforest": _t("forests", "poly", "雨林", "Rainforest", _poly(
        ["#1B6E58", "#D08C2E", "#3E7CB1", "#A2456E", "#6A994E", "#C25B3F", "#4C9A9A", "#8F7FC0"],
        data="#8E9693", env="#1E2B26", bg="#5E6A64")),
    # earth 大地
    "desert": _t("earth", "mono", "沙漠", "Desert",
                 _mono(["#5A3A20", "#7A4E2D", "#B07A45", "#D4A373", "#E9C99A", "#F5E6CA"])),
    "canyon": _t("earth", "mono", "峡谷", "Canyon",
                 _mono(["#4F2116", "#6B2E1F", "#A4452C", "#CF7445", "#E4A47C", "#F3D3BC"])),
    "loess": _t("earth", "soft", "黄土", "Loess", _poly(
        ["#A07A3B", "#C9B07A", "#7B6A4F", "#D9A066", "#8C8C5A", "#B5835A", "#E2CFA3", "#6E5B44"],
        data="#A39C8C", env="#3D3226", bg="#7A7064")),
    "badlands": _t("earth", "poly", "恶地", "Badlands", _poly(
        ["#A4452C", "#4F6D7A", "#C6893F", "#7E6B8F", "#A9A34E", "#5C4033", "#D28A7C", "#3F5E5A"],
        data="#9A928B", env="#2E2622", bg="#6E655F")),
    # skies 天穹
    "dawn": _t("skies", "soft", "晨曦", "Dawn", _poly(
        ["#E08E6D", "#9AA8D8", "#E59BAA", "#F2C38F", "#B79CCF", "#7FB3C8", "#F0A9A0", "#C9B6E4"],
        data="#A7A3B5", env="#4A3F5C", bg="#7D7488", alpha=0.35)),
    "dusk": _t("skies", "poly", "暮色", "Dusk", _poly(
        ["#3B2C5A", "#D56E6B", "#6D3F79", "#EDA06A", "#A5507A", "#F4C987", "#4E5D94", "#C98BB0"],
        data="#9C93A6", env="#24192F", bg="#665A70")),
    "aurora": _t("skies", "poly", "极光", "Aurora", _poly(
        ["#1F9E89", "#3E4A89", "#6CCE59", "#7B4FA8", "#2C728E", "#B4DE2C", "#482878", "#35B779"],
        data="#8C98A0", env="#14202A", bg="#5A6670")),
    "twilight": _t("skies", "mono", "薄暮", "Twilight",
                   _mono(["#1E2540", "#2E3A59", "#4F5D85", "#7F86B0", "#A9A6CC", "#DCD7EC"])),
    # stone 山岩
    "basalt": _t("stone", "mono", "玄武", "Basalt",
                 _mono(["#1A1C1F", "#2E3237", "#4F555C", "#7B8189", "#AEB2B8", "#DDDFE2"])),
    "granite": _t("stone", "mono", "花岗", "Granite",
                  _mono(["#3A3331", "#4A4341", "#7A6E6A", "#A8988F", "#C9B9AF", "#EAE0DA"])),
    "slate": _t("stone", "mono", "板岩", "Slate",
                _mono(["#1C262B", "#263238", "#455A64", "#607D8B", "#90A4AE", "#D5DEE2"])),
    "highland": _t("stone", "soft", "高地", "Highland", _poly(
        ["#332288", "#88CCEE", "#44AA99", "#117733", "#999933", "#DDCC77", "#CC6677", "#882255"],
        data="#9A9A9A", env="#262626", bg="#6A6A6A")),
    # fields 原野
    "lavender": _t("fields", "mono", "薰衣草田", "Lavender",
                   _mono(["#2E1F47", "#3E2A5C", "#6A4C93", "#9A7BC2", "#C5B3E0", "#ECE5F6"])),
    "meadow": _t("fields", "soft", "草甸", "Meadow", _poly(
        ["#5B8E7D", "#F4A259", "#8CB369", "#BC4B51", "#E9D16B", "#6C91BF", "#A27EA8", "#E0A890"],
        data="#9AA39B", env="#283330", bg="#66706A")),
    "autumn": _t("fields", "poly", "秋野", "Autumn", _poly(
        ["#9C2C2C", "#E09F3E", "#3E5641", "#D1603D", "#A3A847", "#7B4B3A", "#C9A66B", "#5E7B8C"],
        data="#A0968D", env="#2B1F1A", bg="#6F655E")),
    "prairie": _t("fields", "cvd", "草原", "Prairie", _poly(
        ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7", "#56B4E9", "#F0E442", "#7F7F7F"],
        data="#999999", env="#222222", bg="#666666")),
}
BUILTIN = list(THEMES)


def _load_user_themes():
    if not os.path.isdir(USER_DIR):
        return
    for f in sorted(os.listdir(USER_DIR)):
        if not f.endswith(".json"):
            continue
        try:
            with open(os.path.join(USER_DIR, f), encoding="utf-8") as fh:
                d = json.load(fh)
            tid = d.get("id") or os.path.splitext(f)[0]
            THEMES["user:" + tid] = dict(
                family="custom", kind=d.get("kind", "poly"), name_zh=d.get("name_zh", tid),
                name_en=d.get("name_en", tid), line_width=d.get("line_width", 1.5),
                data_size=d.get("data_size", 8), font=d.get("font", "Arial"),
                fill_alpha=float(d.get("fill_alpha", 0.3)), data=_hex(d["data"]),
                envelope=_hex(d["envelope"]), background=_hex(d["background"]),
                components=[_hex(c) for c in d["components"]])
        except (OSError, KeyError, ValueError, json.JSONDecodeError):
            continue


def reload_user_themes():
    for k in [k for k in THEMES if k.startswith("user:")]:
        THEMES.pop(k)
    _load_user_themes()


def save_user_theme(tid: str, name_zh: str, name_en: str, spec: dict) -> str:
    """Save a custom theme (colours as tuples or hex strings). Returns its theme id 'user:<tid>'."""
    tid = re.sub(r"[^\w\-]+", "_", tid).strip("_") or "custom"
    os.makedirs(USER_DIR, exist_ok=True)

    def hx(c):
        return c if isinstance(c, str) else to_hex(c)
    d = dict(id=tid, name_zh=name_zh, name_en=name_en, kind=spec.get("kind", "poly"),
             fill_alpha=spec.get("fill_alpha", 0.3), data=hx(spec["data"]), envelope=hx(spec["envelope"]),
             background=hx(spec["background"]), components=[hx(c) for c in spec["components"]])
    with open(os.path.join(USER_DIR, f"{tid}.json"), "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
    reload_user_themes()
    return "user:" + tid


def delete_user_theme(theme_id_: str):
    if theme_id_.startswith("user:"):
        p = os.path.join(USER_DIR, theme_id_[5:] + ".json")
        if os.path.exists(p):
            os.remove(p)
        reload_user_themes()


_load_user_themes()


def theme_id(name: str | None) -> str:
    name = ALIASES.get(name or DEFAULT, name or DEFAULT)
    return name if name in THEMES else DEFAULT


def theme(name: str | None) -> dict:
    return THEMES[theme_id(name)]


def display_name(tid: str, lang: str = "zh") -> str:
    t = theme(tid)
    return f"{t['name_zh']}  {t['name_en']}" if lang == "zh" else f"{t['name_en']}  {t['name_zh']}"


def grouped() -> list[tuple[str, str, str, list[str]]]:
    """[(family_id, zh, en, [theme ids])] in display order."""
    out = []
    for fid, zh, en in FAMILIES:
        ids = [k for k, t in THEMES.items() if t["family"] == fid]
        if ids:
            out.append((fid, zh, en, ids))
    return out


def rgb01(c):
    return tuple(v / 255 for v in c)


def comp_color(th: dict, i: int, override: str | None = None):
    if override:
        return _hex(override)
    return th["components"][i % len(th["components"])]


def region_mathtext(region: str) -> str:
    """'Ir 4f' -> 'Ir 4$\\it{f}$' (italic orbital letter, as in the template)."""
    m = re.match(r"^([A-Z][a-z]?) (\d)([spdf])(.*)$", region)
    if not m:
        return region
    el, n, l, rest = m.groups()
    return f"{el} {n}$\\it{{{l}}}${rest}"


def region_origin(region: str) -> str:
    """Origin rich text: 'Ir 4\\i(f)'."""
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
