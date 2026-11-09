"""Built-in and user model presets + orbital data (spin-orbit splitting, RSF)."""
from __future__ import annotations

import glob
import json
import os
from functools import lru_cache

import numpy as np

from .core import background as bgmod
from .core.model import BackgroundSpec, Component, Param, RegionModel
from .spectrum import Spectrum

DATA = os.path.join(os.path.dirname(__file__), "data")
USER_DIR = os.path.join(os.path.expanduser("~"), ".peakforge", "presets")


@lru_cache(maxsize=1)
def orbitals() -> dict:
    with open(os.path.join(DATA, "orbitals.json"), encoding="utf-8") as f:
        return json.load(f)["orbitals"]


def orbital(region: str) -> dict | None:
    return orbitals().get(region)


def preset_dirs(project_dir: str | None = None) -> list[str]:
    d = [os.path.join(DATA, "presets"), USER_DIR]
    if project_dir:
        d.append(os.path.join(project_dir, "presets"))
    return d


def list_presets(project_dir: str | None = None) -> dict[str, dict]:
    out = {}
    for d in preset_dirs(project_dir):
        for f in sorted(glob.glob(os.path.join(d, "*.json"))):
            try:
                with open(f, encoding="utf-8") as fh:
                    p = json.load(fh)
            except (OSError, json.JSONDecodeError):
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
                    components=[Component.from_json(c) for c in preset.get("components", [])])
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


def generic_model(sp: Spectrum, shift: float = 0.0, n_peaks: int = 1) -> RegionModel:
    """Starting model from orbital data: one singlet/doublet at the strongest feature."""
    orb = orbital(sp.region) or {}
    m = RegionModel(region=sp.region)
    _clip_range(m, sp, shift)
    auto_background(m, sp, shift)
    x = sp.be + shift
    bg = bgmod.compute("shirley", x, sp.cps, m.background.lo, m.background.hi)
    ys = sp.cps - bg
    order = np.argsort(ys)[::-1]
    centers = []
    for i in order:
        if all(abs(x[i] - c) > 1.5 for c in centers):
            centers.append(float(x[i]))
        if len(centers) >= n_peaks:
            break
    for i, c0 in enumerate(centers):
        name = m.unique_name((sp.element or "p") + str(i + 1))
        comp = Component(name=name, label=name, shape="gl",
                         params=dict(center=Param(c0, c0 - 2, c0 + 2), fwhm=Param(1.2, 0.3, 4.0),
                                     m=Param(0.3, 0, 1, vary=False)))
        if orb.get("split"):
            comp.set_doublet(True, orb["split"], orb["ratio"])
            comp.sub_labels = tuple(orb.get("sub") or ("", ""))
        m.components.append(comp)
    scale_areas(m, sp, shift)
    return m
