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


def list_presets(project_dir: str | None = None) -> dict[str, dict]:
    out = {}
    for d in preset_dirs(project_dir):
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            from . import schema
            rep = schema.Report()
            p = schema.load_json(f, rep)
            if p is not None:
                rep.extend(schema.check_preset(p, os.path.basename(f)))
            if not rep.ok:
                log.warning("preset %s skipped: %s", f, rep.text())
                continue
            pid = p.get("id") or os.path.splitext(os.path.basename(f))[0]
            p["id"] = pid
            p["_file"] = f
            p["_builtin"] = d == os.path.join(DATA, "presets")
            out[pid] = p
    return out


def presets_for(region: str, project_dir: str | None = None) -> list[dict]:
    return [p for p in list_presets(project_dir).values() if p.get("region") == region]


def model_from_preset(preset: dict | str, sp: Spectrum | None = None, shift: float = 0.0,
                      project_dir: str | None = None) -> RegionModel:
    if isinstance(preset, str):
        preset = list_presets(project_dir)[preset]
    m = RegionModel(region=preset.get("region", ""), preset=preset.get("id", ""),
                    background=BackgroundSpec.from_json(preset.get("background")),
                    fit_range=tuple(preset["range"]) if preset.get("range") else None,
                    note=preset.get("note_en", ""),
                    components=[Component.from_json(c) for c in preset.get("components", [])],
                    legend_order=list(preset.get("legend_order", [])))
    if sp is not None:
        _clip_range(m, sp, shift)
        auto_background(m, sp, shift)
        scale_areas(m, sp, shift)
    return m


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


def generic_model(sp: Spectrum, shift: float = 0.0, n_peaks: int | None = None,
                  refine: bool = True) -> RegionModel:
    """Starting model for ANY element / core level: peaks found automatically in the data;
    each one a spin–orbit doublet (tabulated split & area ratio) unless the region is an s level,
    a single j sub-level scan (e.g. 'Fe 2p3/2') or a multiplet-dominated level (free singlets)."""
    info = orbital(sp.region) or {}
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
    limit = n_peaks or (6 if info.get("complex") else 4)
    peaks = find_peaks_auto(x[k], ys, split, max_peaks=limit)
    if n_peaks:
        peaks = peaks[:n_peaks]
    el = sp.element or (info.get("element") or "p")
    for i, (c0, w0) in enumerate(sorted(peaks)):
        name = m.unique_name(f"{el}{i + 1}")
        comp = Component(name=name, label=name, shape="gl",
                         params=dict(center=Param(c0, c0 - 1.5, c0 + 1.5),
                                     fwhm=Param(w0, 0.3, max(4.0, w0 * 1.5)),
                                     m=Param(0.3, 0.0, 1.0, vary=False)))
        if doublet:
            comp.set_doublet(True, info["split"], info["ratio"])
            comp.sub_labels = tuple(info.get("sub") or ("", ""))
            _link_split(m, comp, info["split"])
        m.components.append(comp)
    m.note = info.get("note", "")
    scale_areas(m, sp, shift)
    if refine:
        m = refine_by_residual(m, sp, shift, doublet, info, max_add=max(0, limit - len(m.components)))
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
                       max_add: int = 3, rms_target: float = 2.0) -> RegionModel:
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
                         params=dict(center=Param(c0, c0 - 1.0, c0 + 1.0), fwhm=Param(w0, 0.3, 4.0),
                                     m=Param(0.3, 0.0, 1.0, vary=False),
                                     area=Param(max(float(sm[i]), 1e-9) * w0 * 1.06, 0.0)))
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
