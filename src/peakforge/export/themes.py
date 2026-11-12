"""Figure colours, shared by the matplotlib renderer, the GUI and the Origin exporter.

Model (phase 3.6): a *base colour* is chosen per figure and the component colours of that figure are
generated from it.

  BASE_COLORS   named base colours (18 hues 20 deg apart in OKLCH + graphite + slate)
  series()      n harmonious colours from one base: fixed hue (+-15 deg alternating when n > 4), lightness graded,
                neighbours interleaved so that adjacent components contrast; 'gradient' = plain dark-to-light ramp
  COMBOS        landscape-named sets of 6 base colours for a *set of figures*: each element gets the next base of
                the combo (the same element has the same colour in every sample; C and O have fixed neutrals)
  resolve_theme project palette settings + figure key -> theme dict {components, data, envelope, background, ...}

Project storage (settings["palette"]):
  {"combo": "glacier", "assign": {"Ir": "azure"}, "figures": {"<key>": {"base": "teal", "mode": "gradient",
                                                                   "colors": ["#RRGGBB", ...]}}}
User palettes (JSON in ~/.peakforge/themes/, id "user:<id>") give the component colours directly ("manual
sequence"). Old theme ids of version <= 0.2 are mapped to the closest combo (LEGACY_COMBO).
All colours are tuples of 0-255 ints; the generators are deterministic.
"""
from __future__ import annotations

import json
import math
import os
import re

import numpy as np

DEFAULT = "glacier"
DEFAULT_COMBO = DEFAULT
USER_DIR = os.path.join(os.path.expanduser("~"), ".peakforge", "themes")
THEMES: dict[str, dict] = {}      # user palettes only ("user:<id>")


# ---------------------------------------------------------------- colour maths (OKLab / OKLCH)
def _hex(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(c) -> str:
    return "#%02X%02X%02X" % tuple(int(v) for v in c)


def _mix(a, b, t):
    return tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _lin(c: float) -> float:
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _delin(c: float) -> float:
    c = min(1.0, max(0.0, c))
    return 255.0 * (12.92 * c if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055)


def rgb_to_oklab(rgb) -> tuple:
    r, g, b = (_lin(v) for v in rgb)
    l_ = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m_ = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s_ = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def _oklab_to_lin(L: float, a: float, b: float) -> tuple:
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    l, m, s = l_ ** 3, m_ ** 3, s_ ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklab_to_rgb(L: float, a: float, b: float) -> tuple:
    return tuple(int(round(_delin(v))) for v in _oklab_to_lin(L, a, b))


def rgb_to_oklch(rgb) -> tuple:
    L, a, b = rgb_to_oklab(rgb)
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


def oklch_to_rgb(L: float, C: float, h: float) -> tuple:
    """OKLCH -> sRGB; chroma is reduced (hue and lightness kept) until the colour is inside the sRGB gamut."""
    cs, sn = math.cos(math.radians(h)), math.sin(math.radians(h))

    def inside(c):
        return all(-1e-4 <= v <= 1 + 1e-4 for v in _oklab_to_lin(L, c * cs, c * sn))
    if not inside(C):
        lo, hi = 0.0, C
        for _ in range(24):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if inside(mid) else (lo, mid)
        C = lo
    return oklab_to_rgb(L, C * cs, C * sn)


def delta_e(c1, c2) -> float:
    """Euclidean distance in OKLab (about 0.02 = just noticeable, 0.05 = clearly different)."""
    return float(np.linalg.norm(np.subtract(rgb_to_oklab(c1), rgb_to_oklab(c2))))


# ---------------------------------------------------------------- base colours
def _base(h: float, c: float = 0.13, l: float = 0.62) -> str:
    return to_hex(oklch_to_rgb(l, c, h))


_HUES = [(20, "crimson", "绯红"), (40, "coral", "珊瑚"), (60, "amber", "琥珀"), (80, "gold", "金黄"),
         (100, "olive", "橄榄"), (120, "lime", "青柠"), (140, "leaf", "叶绿"), (160, "jade", "翡翠"),
         (180, "teal", "青绿"), (200, "lagoon", "泻湖"), (220, "sky", "天蓝"), (240, "azure", "湛蓝"),
         (260, "cobalt", "钴蓝"), (280, "indigo", "靛蓝"), (300, "violet", "紫罗兰"), (320, "orchid", "兰紫"),
         (340, "magenta", "洋红"), (360, "rose", "玫瑰")]
BASE_COLORS: dict[str, dict] = {k: dict(name_en=k.capitalize(), name_zh=zh, hex=_base(h)) for h, k, zh in _HUES}
BASE_COLORS["graphite"] = dict(name_en="Graphite", name_zh="石墨", hex=_base(60, 0.008, 0.52))
BASE_COLORS["slate"] = dict(name_en="Slate", name_zh="板岩", hex=_base(250, 0.035, 0.55))
FIXED_BASE = {"C": "graphite", "O": "slate"}     # same neutral everywhere: carbon and oxygen are in every sample

COMBOS: dict[str, dict] = {
    "glacier": dict(name_zh="冰川", name_en="Glacier", bases=["azure", "teal", "indigo", "sky", "jade", "cobalt"]),
    "fjord": dict(name_zh="峡湾", name_en="Fjord", bases=["cobalt", "jade", "sky", "violet", "teal", "indigo"]),
    "rainforest": dict(name_zh="雨林", name_en="Rainforest",
                       bases=["jade", "amber", "azure", "magenta", "olive", "coral"]),
    "desert": dict(name_zh="沙漠", name_en="Desert", bases=["amber", "coral", "olive", "cobalt", "gold", "rose"]),
    "canyon": dict(name_zh="峡谷", name_en="Canyon", bases=["crimson", "gold", "teal", "indigo", "coral", "leaf"]),
    "dusk": dict(name_zh="暮色", name_en="Dusk", bases=["indigo", "coral", "orchid", "gold", "azure", "rose"]),
    "aurora": dict(name_zh="极光", name_en="Aurora", bases=["teal", "leaf", "violet", "cobalt", "lime", "magenta"]),
    "meadow": dict(name_zh="草甸", name_en="Meadow", bases=["leaf", "gold", "rose", "sky", "orchid", "teal"]),
}
# theme ids of version <= 0.2 -> closest combo
LEGACY_COMBO = {
    "glacier": "glacier", "fjord": "fjord", "lagoon": "aurora", "abyss": "fjord", "moss": "meadow",
    "pinewood": "rainforest", "bamboo": "meadow", "rainforest": "rainforest", "desert": "desert",
    "canyon": "canyon", "loess": "desert", "badlands": "canyon", "dawn": "dusk", "dusk": "dusk",
    "aurora": "aurora", "twilight": "dusk", "basalt": "fjord", "granite": "desert", "slate": "fjord",
    "highland": "fjord", "lavender": "dusk", "meadow": "meadow", "autumn": "canyon", "prairie": "rainforest",
    "ir_blue": "glacier", "warm": "canyon", "contrast": "rainforest", "muted": "fjord", "gray": "fjord",
}
MODES = ("series", "gradient")


def series(base: str, n: int, mode: str = "series") -> list[tuple]:
    """n component colours generated from one base colour (id or '#RRGGBB').

    mode 'series'  : lightness 0.42-0.86 in n steps, order interleaved dark/light so that neighbours contrast,
                     hue +-15 deg alternating when n > 4;
    mode 'gradient': the same steps, plain dark-to-light, no hue shift.
    n = 1 returns the base itself. Pairwise OKLab distance >= 0.05 for n <= 8 (tests/test_palette.py)."""
    rgb = _hex(BASE_COLORS[base]["hex"] if base in BASE_COLORS else base)
    if n <= 1:
        return [rgb]
    _l0, c0, h0 = rgb_to_oklch(rgb)
    steps = np.linspace(0.42, 0.86, n)
    half = (n + 1) // 2
    order = [j for i in range(half) for j in (i, i + half) if j < n] if mode != "gradient" else list(range(n))
    out = []
    for pos, j in enumerate(order):
        t = j / (n - 1)
        chroma = c0 * (1.0 - 0.35 * abs(2 * t - 1))
        dh = 0.0 if (mode == "gradient" or n <= 4) else 15.0 * (1 if pos % 2 == 0 else -1)
        out.append(oklch_to_rgb(float(steps[j]), chroma, h0 + dh))
    return out


def series_theme(base: str, n: int, mode: str = "series", name: str = "") -> dict:
    """Theme dict for one figure: component colours from `series`; data = softened base, envelope = darkened
    base, background = neutral grey."""
    rgb = _hex(BASE_COLORS[base]["hex"] if base in BASE_COLORS else base)
    _l, c, h = rgb_to_oklch(rgb)
    meta = BASE_COLORS.get(base, {})
    return dict(family="palette", kind="series", name_zh=name or meta.get("name_zh", base),
                name_en=name or meta.get("name_en", base), line_width=1.5, data_size=8,
                font="Arial", fill_alpha=0.30, base=base, components=series(base, max(1, n), mode),
                data=oklch_to_rgb(0.66, 0.45 * c, h), envelope=oklch_to_rgb(0.30, 0.8 * c, h),
                background=oklch_to_rgb(0.50, 0.012, h))


# ---------------------------------------------------------------- assignment of bases to figures
def element_of(region: str | None) -> str | None:
    m = re.match(r"^([A-Z][a-z]?)\b", region or "")
    return m.group(1) if m else None


def resolve_base(palette: dict | None, region: str, regions=()) -> str:
    """Base colour of a region: explicit assignment (region label, then element) > fixed neutral for C / O >
    next base of the combo, in alphabetical order of the elements present in the project."""
    pal = palette or {}
    el = element_of(region)
    asg = pal.get("assign", {}) or {}
    for k in (region, el):
        if k and asg.get(k) in BASE_COLORS:
            return asg[k]
    if el in FIXED_BASE:
        return FIXED_BASE[el]
    combo = COMBOS.get(pal.get("combo")) or COMBOS[DEFAULT_COMBO]
    pool = [b for b in combo["bases"] if b not in FIXED_BASE.values()] or combo["bases"]
    elems = sorted({e for e in (element_of(r) for r in list(regions) + [region]) if e and e not in FIXED_BASE})
    i = elems.index(el) if el in elems else 0
    return pool[i % len(pool)]


def resolve_theme(palette: dict | None, key: str | None, region: str, regions=(), n: int = 8) -> dict:
    """The one place that decides the colours of a figure (GUI canvas, PNG/SVG/PDF, Excel, Origin).
    Priority: manual colours of the figure > base / mode of the figure > project combo (or a user palette)."""
    pal = palette or {}
    combo = pal.get("combo", DEFAULT_COMBO)
    fig = (pal.get("figures", {}) or {}).get(key, {}) if key else {}
    if combo in THEMES and fig.get("base") not in BASE_COLORS:     # user palette: manual sequence
        th = dict(THEMES[combo])
    else:
        base = fig.get("base") if fig.get("base") in BASE_COLORS else resolve_base(pal, region, regions)
        mode = fig.get("mode") or pal.get("mode") or "series"
        th = series_theme(base, n, mode if mode in MODES else "series")
    cols = [c for c in (fig.get("colors") or []) if isinstance(c, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", c)]
    if cols:
        th["components"] = [_hex(c) for c in cols]
    return th


def legacy_palette(theme_id_: str | None) -> dict:
    """Palette settings equivalent to an old `settings["theme"]` value."""
    t = theme_id_ or DEFAULT
    if t in THEMES:
        return dict(combo=t)
    return dict(combo=LEGACY_COMBO.get(t, t if t in COMBOS else DEFAULT_COMBO))


# ---------------------------------------------------------------- user palettes
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
    """Save a custom palette (colours as tuples or hex strings). Returns its id 'user:<tid>'."""
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


# ---------------------------------------------------------------- lookups used by renderers and the GUI
def theme_id(name: str | None) -> str:
    """Normalise a combo / user-palette / legacy theme id to a valid combo or user id."""
    if name in COMBOS or name in THEMES:
        return name
    return legacy_palette(name)["combo"]


def theme(name) -> dict:
    """Theme dict from a dict (passed through), a user palette id, or a combo id (first base, 8 components)."""
    if isinstance(name, dict):
        return name
    tid = theme_id(name)
    if tid in THEMES:
        return THEMES[tid]
    return series_theme(COMBOS[tid]["bases"][0], 8, name=COMBOS[tid]["name_en"])


def preview_colors(tid: str) -> list[tuple]:
    """Swatch colours of a combo (its bases) or user palette (its components)."""
    tid = theme_id(tid)
    if tid in THEMES:
        return list(THEMES[tid]["components"][:6])
    return [_hex(BASE_COLORS[b]["hex"]) for b in COMBOS[tid]["bases"]]


def display_name(tid: str, lang: str = "zh") -> str:
    tid = theme_id(tid)
    t = THEMES.get(tid) or COMBOS[tid]
    return f"{t['name_zh']}  {t['name_en']}" if lang == "zh" else f"{t['name_en']}  {t['name_zh']}"


def grouped() -> list[tuple[str, str, str, list[str]]]:
    """[(group_id, zh, en, [combo / user palette ids])] in display order."""
    out = [("combos", "配色组合", "Combos", list(COMBOS))]
    users = [k for k in THEMES if k.startswith("user:")]
    if users:
        out.append(("custom", "自定义", "Custom", users))
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
