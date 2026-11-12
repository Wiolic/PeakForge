"""Built-in and user model presets + orbital data (spin-orbit splitting, RSF)."""
from __future__ import annotations

import glob
import json
import os
from functools import lru_cache

import numpy as np

from .core import background as bgmod
from .core.model import BackgroundSpec, Component, Param, RegionModel
from .logs import log
from .spectrum import Spectrum

DATA = os.path.join(os.path.dirname(__file__), "data")
USER_DIR = os.path.join(os.path.expanduser("~"), ".peakforge", "presets")


@lru_cache(maxsize=1)
def orbitals() -> dict:
    """Core-level table (read once; treat as read-only)."""
    with open(os.path.join(DATA, "orbitals.json"), encoding="utf-8") as f:
        return json.load(f)["orbitals"]


def orbital(region: str) -> dict | None:
    """Core-level info for a region label.
    'Fe 2p' → table entry; 'Fe 2p3/2' / 'Fe 2p1/2' → same level flagged subshell=True (single line,
    no doublet; be shifted by the split for the low-j partner); 'Ta' → the element's main level."""
    import re
    if not region:
        return None
    tab = orbitals()
    r = region.strip()
    if r in tab:
        return dict(tab[r])
    m = re.match(r"^([A-Z][a-z]?) (\d[spdf])(\d/2)$", r)
    if m and f"{m.group(1)} {m.group(2)}" in tab:
        d = dict(tab[f"{m.group(1)} {m.group(2)}"])
        d["subshell"] = True
        sub = d.get("sub") or []
        if sub and d.get("split") and r.endswith(sub[-1][len(m.group(2)):]):   # low-j partner scanned alone
            d["be"] = d["be"] + d["split"]
        d["level_split"] = d.get("split")
        d["split"], d["ratio"], d["sub"] = None, None, None        # one line only → singlets
        return d
    if re.match(r"^[A-Z][a-z]?$", r):
        mains = [v for v in tab.values() if v["element"] == r and v.get("main")]
        if mains:
            return dict(mains[0])
    return None


def orbital_choices() -> list[tuple[str, str]]:
    """[(region key, display)] sorted by Z — for 'assign element / core level' pickers."""
    out = []
    for k, v in orbitals().items():
        extra = f", Δ {v['split']} eV" if v.get("split") else ""
        out.append((k, f"{v['z']:>2}  {k}   (~{v['be']:g} eV{extra})"))
    return out


def preset_dirs(project_dir: str | None = None) -> list[str]:
    d = [os.path.join(DATA, "presets"), USER_DIR]
    if project_dir:
        d.append(os.path.join(project_dir, "presets"))
    return d


_CHECKED: dict[str, tuple[float, int, dict | None]] = {}     # path -> (mtime, size, preset or None)


def _load_checked(f: str) -> dict | None:
    """Read + validate a preset file once per (mtime, size); None when it has errors."""
    try:
        st = os.stat(f)
    except OSError:
        return None
    hit = _CHECKED.get(f)
    if hit and hit[:2] == (st.st_mtime, st.st_size):
        return None if hit[2] is None else dict(hit[2])
    from . import schema
    rep = schema.Report()
    p = schema.load_json(f, rep)
    if p is not None:
        rep.extend(schema.check_preset(p, os.path.basename(f)))
    if not rep.ok:
        log.warning("preset %s skipped: %s", f, rep.text())
        p = None
    _CHECKED[f] = (st.st_mtime, st.st_size, p)
    return None if p is None else dict(p)


@lru_cache(maxsize=1)
def multiplet_tables() -> dict:
    with open(os.path.join(DATA, "multiplets.json"), encoding="utf-8") as f:
        return json.load(f)["tables"]


def _ident(s: str) -> str:
    import re
    return re.sub(r"\W", "", s.replace("(", "").replace(")", "")) or "s"


def multiplet_preset(tid: str, species: list[str] | None = None) -> dict:
    """Preset (same structure as the JSON presets) built from a sourced multiplet table, for any element.
    Each species is a group: its first peak has a free position (table ± 0.4 eV) and a free area; the other
    peaks follow at the tabulated offsets and area ratios. Widths keep the tabulated ratios and scale
    together (one free factor 0.8–1.4 per species) for a different instrument resolution. For a table of the
    high-j line only (part 'high_j') the window stops 1.5 eV before the low-j partner of the lowest main line,
    as in the source (fit 2p3/2 only); quantification then uses the high-j share of the RSF.
    `species`: subset to include (default all). Envelopes of different species overlap strongly, so only
    species supported by other evidence should be combined (METHODS §6c); these presets are never applied
    automatically."""
    t = multiplet_tables()[tid]
    info = orbital(t["level"]) or {}
    comps, mains = [], []
    chosen = {k: v for k, v in t["species"].items() if species is None or k in species}
    for sp_name, peaks in chosen.items():
        base = _ident(sp_name)
        be1, a1, w1 = peaks[0]
        n1 = f"{base}_1"
        mains.append(be1)
        for i, (be, a, w) in enumerate(peaks, start=1):
            name = f"{base}_{i}"
            par = dict(m=dict(value=t.get("m", 0.3), vary=False))
            if i == 1:
                par.update(center=dict(value=be1, min=be1 - 0.4, max=be1 + 0.4),
                           fwhm=dict(value=w1, min=0.8 * w1, max=1.4 * w1),
                           area=dict(value=1.0, min=0.0))
            else:
                par.update(center=dict(value=be, expr=f"{n1}.center + {be - be1:.4g}"),
                           fwhm=dict(value=w, expr=f"{n1}.fwhm * {w / w1:.6g}"),
                           area=dict(value=a / a1, expr=f"{n1}.area * {a / a1:.6g}"))
            comps.append(dict(name=name, label=f"{sp_name} {i}" if len(peaks) > 1 else sp_name,
                              shape=t.get("shape", "gl"), params=par))
    allp = [x for peaks in chosen.values() for x in peaks]
    lo = min(be for be, _a, _w in allp) - 4.0
    hi = max(be for be, _a, _w in allp) + 2.5
    if t.get("part") == "high_j" and info.get("split"):        # stop before the low-j line of the selected species
        hi = min(hi, min(p[0][0] for p in chosen.values()) + info["split"] - 1.5)
    tag = "" if species is None else ":" + "+".join(species)
    label = "all species" if species is None else " + ".join(species)
    return dict(id=f"multiplet_{tid}{tag}", name_en=f"{t['name_en']}: {label}",
                name_zh=f"{t.get('name_zh', t['name_en'])}：{'全部化学态' if species is None else label}",
                region=t["level"], level=t["level"], part=t.get("part", ""), range=[round(lo, 2), round(hi, 2)],
                background=dict(kind="shirley"), components=comps, source=t["source"], auto=False,
                note_en=(f"Species envelopes from: {t['source']} Keep only species supported by other evidence; "
                         "area fractions depend strongly on the high-BE background end point (METHODS §6c)."),
                note_zh=(f"化学态包络出处：{t['source']} 只保留有其他证据支持的化学态；占比强烈依赖高 BE 端背景端点"
                         "（METHODS §6c）。"),
                _builtin=True, _file=os.path.join(DATA, "multiplets.json"))


@lru_cache(maxsize=1)
def _multiplet_presets() -> tuple[dict, ...]:
    """All-species and single-species presets of every multiplet table (immutable data: built once)."""
    return tuple(multiplet_preset(tid, sel) for tid, t in multiplet_tables().items()
                 for sel in [None] + [[s] for s in t["species"]])


def list_presets(project_dir: str | None = None) -> dict[str, dict]:
    out = {p["id"]: dict(p) for p in _multiplet_presets()}
    for d in preset_dirs(project_dir):
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            p = _load_checked(f)
            if p is None:
                continue
            pid = p.get("id") or os.path.splitext(os.path.basename(f))[0]
            p["id"] = pid
            p["_file"] = f
            p["_builtin"] = d == os.path.join(DATA, "presets")
            out[pid] = p
    return out


def presets_for(region: str, project_dir: str | None = None) -> list[dict]:
    """Presets for a region label; level presets (multiplet tables) also match sub-level labels such as
    'Co 2p3/2' (instruments name the window after the main line)."""
    o = orbital(region) or {}
    lvl = f"{o.get('element')} {o.get('level')}" if o else None
    return [p for p in list_presets(project_dir).values()
            if p.get("region") == region or (p.get("level") and p["level"] == lvl)]


def high_j_only(model: RegionModel) -> bool:
    """True when the model comes from a table that covers only the high-j line (quantification scales the RSF)."""
    if not model.preset.startswith("multiplet_"):
        return False
    t = multiplet_tables().get(model.preset[len("multiplet_"):].split(":")[0])
    return bool(t) and t.get("part") == "high_j"


def model_from_preset(preset: dict | str, sp: Spectrum | None = None, shift: float = 0.0,
                      project_dir: str | None = None) -> RegionModel:
    if isinstance(preset, str):
        preset = list_presets(project_dir)[preset]
    m = RegionModel(region=sp.region if sp is not None else preset.get("region", ""), preset=preset.get("id", ""),
                    background=BackgroundSpec.from_json(preset.get("background")),
                    fit_range=tuple(preset["range"]) if preset.get("range") else None,
                    note=preset.get("note_en", ""),
                    components=[Component.from_json(c) for c in preset.get("components", [])],
                    legend_order=list(preset.get("legend_order", [])))
    if sp is not None:
        _clip_range(m, sp, shift)
        auto_background(m, sp, shift)
        fit_to_window(m, sp, shift)
        scale_areas(m, sp, shift)
    return m


OVERLAP_SHIFT = 4.0     # eV: tabulated (mostly elemental) positions; compounds lie up to a few eV higher


def overlapping_levels(region: str, elements: set[str], lo: float, hi: float) -> list[dict]:
    """Other core levels that can lie inside the window lo–hi (corrected BE) of `region`: every level in
    the orbital table of an element in `elements` (the elements measured in the same sample, including the
    region's own) whose main line or spin–orbit partner, shifted by 0 … OVERLAP_SHIFT eV, falls in the
    window. Data-driven for all elements; the table values are approximate, so this is a warning list."""
    own = orbital(region) or {}
    own_key = f"{own.get('element')} {own.get('level')}" if own else region
    out = []
    for key, v in orbitals().items():
        if v["element"] not in elements or key == own_key or v.get("be") is None:
            continue
        lines = [v["be"]] + ([v["be"] + v["split"]] if v.get("split") else [])
        hit = [e for e in lines if e + OVERLAP_SHIFT >= lo and e <= hi]
        if hit:
            out.append(dict(level=key, be=float(v["be"]), lines=[round(float(e), 2) for e in hit]))
    return out


def fit_to_window(m: RegionModel, sp: Spectrum, shift: float = 0.0):
    """Adapt a model's bounds to the data it will be fitted to (any preset, any element):
    free FWHM minima are raised to the resolution/sampling floor (core.quality.resolution_floor), and
    free centre bounds are pulled 0.1 eV inside the fit window, so a component cannot wander onto
    the window edge and fit the next feature. Components whose start position lies outside the window
    cannot be determined by these data and are removed (unless another parameter refers to them; then
    the quality check reports them); the model note says which."""
    from .core import quality
    if not m.fit_range:
        return
    a, b = sorted(m.fit_range)
    x = sp.be + shift
    k = (x >= a) & (x <= b)
    floor = quality.resolution_floor(x[k]) if k.sum() > 2 else quality.MIN_FWHM_INSTRUMENT
    outside = {c.name for c in m.components if "center" in c.params and not a <= c.params["center"].value <= b}
    # keep an outside component only while a component that stays refers to it (repeat: chains)
    while True:
        exprs = " ".join(p.expr or "" for c in m.components if c.name not in outside for p in c.params.values())
        keep = {n for n in outside if f"{n}." in exprs}
        if not keep:
            break
        outside -= keep
    out = [c for c in m.components if c.name in outside]
    if out and len(out) < len(m.components):
        gone = {c.name for c in out}
        m.components = [c for c in m.components if c.name not in gone]
        m.legend_order = [n for n in m.legend_order if n not in gone]
        m.note = (m.note + " " if m.note else "") + (
            "Not in the scanned window, removed: " + ", ".join(c.label or c.name for c in out) + ".")
    for c in m.components:
        w = c.params.get("fwhm")
        if w is not None and w.free and w.min < floor:
            w.min = floor
            w.max = max(w.max, floor * 1.5)
            w.value = min(max(w.value, floor * 1.2), w.max)
        ce = c.params.get("center")
        if ce is not None and ce.free and a <= ce.value <= b:
            ce.min, ce.max = max(ce.min, a + 0.1), min(ce.max, b - 0.1)
            ce.value = min(max(ce.value, ce.min), ce.max)


def auto_background(m: RegionModel, sp: Spectrum, shift: float = 0.0):
    """Pick background end points inside the fit range and shrink the fit range to them."""
    x = sp.be + shift
    a, b = sorted(m.fit_range) if m.fit_range else (x.min(), x.max())
    k = (x >= a) & (x <= b)
    if k.sum() < 10:
        return
    lo, hi = bgmod.auto_limits(x[k], sp.cps[k])
    m.background.lo, m.background.hi = round(lo, 2), round(hi, 2)
    m.fit_range = (round(lo, 2), round(hi, 2))


def save_user_preset(model: RegionModel, pid: str, name_en: str, name_zh: str = "",
                     project_dir: str | None = None) -> str:
    d = os.path.join(project_dir, "presets") if project_dir else USER_DIR
    os.makedirs(d, exist_ok=True)
    js = model.to_json()
    p = dict(id=pid, name_en=name_en, name_zh=name_zh or name_en, region=model.region,
             range=js["fit_range"], background=js["background"], components=js["components"],
             legend_order=js.get("legend_order", []),
             note_en=model.note, note_zh=model.note)
    path = os.path.join(d, f"{pid}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
    return path


def _clip_range(m: RegionModel, sp: Spectrum, shift: float):
    lo, hi = sp.be.min() + shift, sp.be.max() + shift
    if m.fit_range:
        a, b = sorted(m.fit_range)
        a, b = max(a, lo), min(b, hi)
        m.fit_range = (a, b) if b - a > 1 else (lo, hi)
    else:
        m.fit_range = (lo, hi)


def scale_areas(m: RegionModel, sp: Spectrum, shift: float = 0.0):
    """Initial areas from the data: each component gets (local height above background) × FWHM."""
    x = sp.be + shift
    y = sp.cps
    if m.fit_range:
        a, b = sorted(m.fit_range)
        k = (x >= a) & (x <= b)
        x, y = x[k], y[k]
    bg = bgmod.compute(m.background.kind, x, y, m.background.lo, m.background.hi, m.background.avg)
    ys = np.clip(y - bg, 0, None)
    vals = m.resolve()
    for c in m.components:
        p = c.params["area"]
        if p.expr:
            continue
        v = vals[c.name]
        h = float(np.interp(v["center"], x, ys)) if len(x) else 1.0
        w = max(v["fwhm"], 0.3)
        p.value = max(h * w * 1.06, 1e-6 * max(ys.max(), 1.0))
        p.min = 0.0


def find_peaks_auto(x: np.ndarray, ys: np.ndarray, split: float | None = None, max_peaks: int = 4,
                    min_rel: float = 0.08) -> list[tuple[float, float]]:
    """Peaks of a background-subtracted spectrum → [(centre, fwhm)], strongest first.
    With a spin–orbit `split`, a peak sitting at (stronger peak + split) is treated as its partner
    and dropped, so each returned position is the main (lower-BE) line of one chemical state."""
    from scipy.signal import find_peaks, peak_widths
    o = np.argsort(x)
    x, ys = x[o], ys[o]
    if len(x) < 7:
        return [(float(x[np.argmax(ys)]), 1.2)]
    dx = float(np.median(np.diff(x))) or 0.1
    k = max(3, int(round(0.4 / dx)) | 1)                     # ~0.4 eV smoothing window
    sm = np.convolve(ys, np.ones(k) / k, mode="same")
    top = float(sm.max())
    if top <= 0:
        return [(float(x[np.argmax(ys)]), 1.2)]
    idx, prop = find_peaks(sm, prominence=min_rel * top, distance=max(1, int(0.5 / dx)))
    if len(idx) == 0:
        idx = np.array([int(np.argmax(sm))])
    widths = peak_widths(sm, idx, rel_height=0.5)[0] * dx
    cand = sorted(zip(idx, widths), key=lambda t: -sm[t[0]])
    out: list[tuple[float, float]] = []
    for i, w in cand:
        c = float(x[i])
        if split and any(abs(c - (oc + split)) < max(0.4, 0.25 * split) for oc, _ in out):
            continue                                          # spin–orbit partner of an accepted peak
        if split and any(abs(oc - (c + split)) < max(0.4, 0.25 * split) for oc, _ in out):
            # accepted peak is actually the partner of this one (weaker main line can't happen for
            # ratio < 1, but keep the lower-BE assignment consistent)
            continue
        out.append((c, float(np.clip(w, 0.5, 4.0))))
        if len(out) >= max_peaks:
            break
    return out


def _above_line(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(sorted x, smoothed signal above a straight line through the window ends)."""
    o = np.argsort(x)
    x, y = x[o], y[o]
    n = max(2, len(x) // 20)
    y0, y1 = float(np.mean(y[:n])), float(np.mean(y[-n:]))
    line = y0 + (y1 - y0) * (x - x[0]) / max(x[-1] - x[0], 1e-9)
    k = max(3, int(round(0.4 / (float(np.median(np.diff(x))) or 0.1))) | 1)
    return x, np.convolve(y - line, np.ones(k) / k, mode="same")


def _main_peak(x: np.ndarray, y: np.ndarray) -> float:
    """Position of the strongest feature above a straight line through the window ends."""
    xs, sm = _above_line(x, y)
    return float(xs[int(np.argmax(sm))])


def _is_low_j(region: str, info: dict) -> bool:
    full = orbital(f"{info['element']} {info['level']}") or {}
    sub = full.get("sub") or ["", ""]
    return bool(sub[-1]) and region.endswith(sub[-1][len(info["level"]):])


def covers_partner(sp: Spectrum) -> bool:
    """True when a region labelled as one j sub-level ('Ag 3d5/2', 'Co 2p3/2') actually covers the
    spin–orbit partner too: instruments name regions after the main line, the window decides.
    The partner of the strongest feature must lie inside the window with 1.5 eV to spare AND carry at least
    25 % of the intensity the tabulated area ratio predicts (a wide window without the partner stays one line)."""
    info = orbital(sp.region) or {}
    s = info.get("level_split")
    if not info.get("subshell") or not s or len(sp.be) < 7:
        return False
    xs, sm = _above_line(sp.be, sp.cps)
    i = int(np.argmax(sm))
    c, h = float(xs[i]), float(sm[i])
    low_j = _is_low_j(sp.region, info)
    partner = c - s if low_j else c + s
    if not float(xs[0]) + 1.5 <= partner <= float(xs[-1]) - 1.5 or h <= 0:
        return False
    r = (orbital(f"{info['element']} {info['level']}") or {}).get("ratio") or 0.5
    expect = h / r if low_j else h * r
    k = np.abs(xs - partner) <= 0.75
    return bool(k.any()) and float(sm[k].max()) >= 0.25 * expect


def subshell_fraction(sp: Spectrum) -> float:
    """Share of the level's intensity in this scan: 1 for a full level (or a sub-level label whose window
    covers both partners); 1/(1+r) for the high-j and r/(1+r) for the low-j line scanned alone
    (r = tabulated low-j / high-j area ratio)."""
    info = orbital(sp.region) or {}
    if not info.get("subshell") or covers_partner(sp):
        return 1.0
    r = (orbital(f"{info['element']} {info['level']}") or {}).get("ratio")
    if not r:
        return 1.0
    return r / (1 + r) if _is_low_j(sp.region, info) else 1 / (1 + r)


def generic_model(sp: Spectrum, shift: float = 0.0, n_peaks: int | None = None,
                  refine: bool = True) -> RegionModel:
    """Starting model for ANY element / core level: peaks found automatically in the data;
    each one a spin–orbit doublet (tabulated split & area ratio) unless the region is an s level,
    a single j sub-level scan (e.g. 'Fe 2p3/2' whose window holds only that line) or a
    multiplet-dominated level (free singlets). Widths cannot go below the resolution/sampling floor
    (core.quality.resolution_floor); at low S/N (< core.quality.LOW_SNR) fewer components are placed
    and they share one FWHM, because the data cannot determine more parameters."""
    from .core import quality
    info = orbital(sp.region) or {}
    if covers_partner(sp):                    # label says one sub-level, the window holds both
        info = orbital(f"{info['element']} {info['level']}") or info
    m = RegionModel(region=sp.region)
    _clip_range(m, sp, shift)
    auto_background(m, sp, shift)
    x = sp.be + shift
    a, b = sorted(m.fit_range)
    k = (x >= a) & (x <= b)
    bg = bgmod.compute("shirley", x[k], sp.cps[k], m.background.lo, m.background.hi)
    ys = sp.cps[k] - bg
    doublet = bool(info.get("split")) and not info.get("subshell") and not info.get("complex")
    split = info.get("split") if doublet else None
    floor = quality.resolution_floor(x[k])
    t = sp.acq_time()
    sigma = np.sqrt(np.clip(sp.cps[k] * t, 1.0, None)) / t if t else None
    low_snr = quality.peak_snr(x[k], sp.cps[k], bg, sigma) < quality.LOW_SNR
    limit = n_peaks or ((3 if info.get("complex") else 2) if low_snr else (6 if info.get("complex") else 4))
    peaks = find_peaks_auto(x[k], ys, split, max_peaks=limit)
    if n_peaks:
        peaks = peaks[:n_peaks]
    el = sp.element or (info.get("element") or "p")
    for i, (c0, w0) in enumerate(sorted(peaks)):
        name = m.unique_name(f"{el}{i + 1}")
        w0 = max(w0, floor * 1.2)
        comp = Component(name=name, label=name, shape="gl",
                         params=dict(center=Param(c0, c0 - 1.5, c0 + 1.5),
                                     fwhm=Param(w0, floor, max(4.0, w0 * 1.5)),
                                     m=Param(0.3, 0.0, 1.0, vary=False)))
        if low_snr and m.components and not info.get("complex"):
            comp.params["fwhm"].expr = f"{m.components[0].name}.fwhm"
        if doublet:
            comp.set_doublet(True, info["split"], info["ratio"])
            comp.sub_labels = tuple(info.get("sub") or ("", ""))
            _link_split(m, comp, info["split"])
        m.components.append(comp)
    m.note = info.get("note", "")
    if low_snr:
        m.note = (m.note + " " if m.note else "") + ("Low S/N: few components with a shared FWHM; add more "
                                                      "only with chemical justification.")
    scale_areas(m, sp, shift)
    if refine:
        m = refine_by_residual(m, sp, shift, doublet, info, max_add=max(0, limit - len(m.components)),
                               floor=floor, shared_fwhm=low_snr and not info.get("complex"))
    return m


def _link_split(m: RegionModel, comp: Component, split: float):
    """Spin–orbit splitting depends slightly on chemical state (e.g. Ti 2p: 6.1 metal, 5.7 oxide):
    the first doublet gets it free within ±7 % of the table value, all others are linked to it."""
    first = next((c for c in m.components if c.doublet), None)
    if first is None:
        if split < 1.0:                       # unresolvable next to typical widths: keep the table value
            comp.params["split"] = Param(split, vary=False)
        else:
            d = 0.07 * split
            comp.params["split"] = Param(split, split - d, split + d)
    else:
        comp.params["split"] = Param(first.params["split"].value, expr=f"{first.name}.split")


def refine_by_residual(m: RegionModel, sp: Spectrum, shift: float, doublet: bool, info: dict,
                       max_add: int = 3, rms_target: float = 2.0, floor: float = 0.5,
                       shared_fwhm: bool = False) -> RegionModel:
    """Shoulders are invisible to peak search: fit, put a new component at the largest positive
    residual, keep it only if BIC drops by > 10. Repeats up to max_add times."""
    from .core.fit import apply_result, fit, prepare
    prep = prepare(sp.be, sp.cps, m, shift)
    best = fit(m, prep, n_starts=1)
    apply_result(m, best)
    el = sp.element or (info.get("element") or "p")
    for _ in range(max_add):
        if best.rms_pct < rms_target:
            break
        o = np.argsort(best.x)
        x, res = best.x[o], best.residual[o]
        k = max(3, int(round(0.5 / (np.median(np.diff(x)) or 0.1))) | 1)
        sm = np.convolve(res, np.ones(k) / k, mode="same")
        i = int(np.argmax(sm))
        if sm[i] <= 0:
            break
        c0 = float(x[i])
        if doublet:                       # residual may sit on a partner line: map back to the main line
            s_ = info["split"]
            near_main = min((abs(c0 - s_ - v["center"]) for v in best.values.values()), default=9)
            if near_main < 0.5 and c0 - s_ >= x.min():
                c0 -= s_
        trial = m.copy()
        w0 = float(np.median([c.params["fwhm"].value for c in m.components])) if m.components else 1.2
        comp = Component(name=trial.unique_name(f"{el}{len(m.components) + 1}"), shape="gl",
                         params=dict(center=Param(c0, c0 - 1.0, c0 + 1.0),
                                     fwhm=Param(max(w0, floor), floor, 4.0),
                                     m=Param(0.3, 0.0, 1.0, vary=False),
                                     area=Param(max(float(sm[i]), 1e-9) * w0 * 1.06, 0.0)))
        if shared_fwhm and trial.components:
            comp.params["fwhm"].expr = f"{trial.components[0].name}.fwhm"
        if doublet:
            comp.set_doublet(True, info["split"], info["ratio"])
            comp.sub_labels = tuple(info.get("sub") or ("", ""))
            _link_split(trial, comp, info["split"])
        trial.components.append(comp)
        r = fit(trial, prepare(sp.be, sp.cps, trial, shift), n_starts=1)
        if r.bic < best.bic - 10:
            apply_result(trial, r)
            m, best = trial, r
        else:
            break
    return m
