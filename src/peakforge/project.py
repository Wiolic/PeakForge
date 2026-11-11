"""PeakForge project (.xpsproj).

Layout (one folder per project):
    <name>.xpsproj          project file (JSON): files, samples, charge shifts, settings
    data/raw/               copies of imported raw files (read-only)
    models/<key>.json       peak model + last fit summary per spectrum
    presets/                project-specific presets
    output/                 everything generated (figures, Origin, Excel) — safe to delete
The GUI and the MCP server both read/write this folder; the GUI reloads when files change.
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import shutil
import stat

import numpy as np

from . import __version__, presets
from .core import quant
from .core.fit import FitResult, apply_result, fit, prepare
from .core.model import RegionModel
from .io import load_file
from .spectrum import Spectrum

EXT = ".xpsproj"


def _now():
    return _dt.datetime.now().isoformat(timespec="seconds")


def safe_name(key: str) -> str:
    return re.sub(r"[^\w\-.()+]+", "_", key, flags=re.UNICODE).strip("_")


def find_project(path: str) -> str:
    """Accept a .xpsproj file or a folder containing one."""
    if os.path.isfile(path) and path.endswith(EXT):
        return os.path.abspath(path)
    if os.path.isdir(path):
        c = [f for f in os.listdir(path) if f.endswith(EXT)]
        if c:
            return os.path.abspath(os.path.join(path, sorted(c)[0]))
    raise FileNotFoundError(f"No {EXT} project at {path}")


class Project:
    def __init__(self, path: str, data: dict):
        self.path = os.path.abspath(path)
        self.root = os.path.dirname(self.path)
        self.data = data
        self.spectra: dict[str, Spectrum] = {}
        self.results: dict[str, FitResult] = {}
        self.charge_failures: dict[str, str] = {}
        self._load_spectra()

    # ------------------------------------------------------------------ create / open / save
    @classmethod
    def create(cls, folder: str, name: str | None = None) -> "Project":
        name = name or os.path.basename(os.path.abspath(folder))
        os.makedirs(folder, exist_ok=True)
        for d in ("data/raw", "models", "presets", "output"):
            os.makedirs(os.path.join(folder, d), exist_ok=True)
        path = os.path.join(folder, safe_name(name) + EXT)
        if os.path.exists(path):
            return cls.open(path)
        data = dict(format="peakforge-project", version=__version__, name=name, created=_now(),
                    modified=_now(), settings=dict(charge_ref=284.8, lang="zh", theme="glacier"),
                    files=[], samples={})
        p = cls(path, data)
        p.save()
        return p

    @classmethod
    def open(cls, path: str) -> "Project":
        path = find_project(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if data.get("format") != "peakforge-project":
            raise ValueError(f"{path} is not a PeakForge project")
        return cls(path, data)

    def save(self):
        self.data["modified"] = _now()
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self.path)

    def reload(self):
        with open(self.path, encoding="utf-8") as f:
            self.data = json.load(f)
        self._load_spectra()

    @property
    def name(self) -> str:
        return self.data.get("name", "")

    @property
    def settings(self) -> dict:
        return self.data.setdefault("settings", {})

    def out_dir(self, *sub: str) -> str:
        d = os.path.join(self.root, "output", *sub)
        os.makedirs(d, exist_ok=True)
        return d

    # ------------------------------------------------------------------ data
    def _load_spectra(self):
        self.spectra.clear()
        for f in self.data.get("files", []):
            p = os.path.join(self.root, f["path"])
            try:
                sps = load_file(p)
            except Exception as e:      # noqa: BLE001
                f["error"] = str(e)
                continue
            ov = self.data.get("region_override", {})
            for s in sps:
                s.sample = f["sample"]
                orig = s.key
                if orig in ov:
                    s.meta["orig_region"] = s.region
                    s.meta["orig_key"] = orig
                    s.region = ov[orig]
                self.spectra[s.key] = s

    def set_region(self, key: str, region: str) -> str:
        """Assign the element / core level of a spectrum (e.g. a CSV column called 'Sample1' → 'Fe 2p').
        The model file moves with the spectrum. Returns the new key."""
        from .spectrum import normalize_region
        s = self.spectra[key]
        region = normalize_region(region)
        orig = s.meta.get("orig_key", key)
        self.data.setdefault("region_override", {})[orig] = region
        old_model = self._model_path(key)
        self.save()
        self._load_spectra()
        new_key = next(k for k, sp in self.spectra.items() if sp.meta.get("orig_key", k) == orig)
        if os.path.exists(old_model) and new_key != key:
            os.replace(old_model, self._model_path(new_key))
        self.results.pop(key, None)
        return new_key

    def add_file(self, src: str, sample: str | None = None, copy: bool = True) -> list[str]:
        src = os.path.abspath(src)
        sps = load_file(src)                      # validate before copying
        if not sps:
            raise ValueError(f"No spectra found in {src}")
        base = os.path.splitext(os.path.basename(src))[0]
        sample = sample or base
        existing = {f["sample"] for f in self.data["files"]}
        if sample in existing:
            ext = os.path.splitext(src)[1].lstrip(".").lower()
            cand, i = f"{sample} ({ext})", 2
            while cand in existing:
                cand, i = f"{sample} ({ext}{i})", i + 1
            sample = cand
        if copy:
            dst_dir = os.path.join(self.root, "data", "raw")
            os.makedirs(dst_dir, exist_ok=True)
            dst = os.path.join(dst_dir, os.path.basename(src))
            if os.path.exists(dst) and os.path.abspath(dst) != src:
                stem, ext = os.path.splitext(dst)
                i = 2
                while os.path.exists(f"{stem}_{i}{ext}"):
                    i += 1
                dst = f"{stem}_{i}{ext}"
            if os.path.abspath(dst) != src:
                shutil.copy2(src, dst)
                os.chmod(dst, stat.S_IREAD | stat.S_IRGRP | stat.S_IROTH)
            rel = os.path.relpath(dst, self.root)
        else:
            rel = os.path.relpath(src, self.root)
        self.data["files"].append(dict(path=rel.replace("\\", "/"), sample=sample,
                                       format=sps[0].meta.get("format", ""), added=_now()))
        self.data["samples"].setdefault(sample, dict(shift=0.0, shift_source="none", label=sample))
        keys = []
        for s in sps:
            s.sample = sample
            self.spectra[s.key] = s
            keys.append(s.key)
        self.save()
        return keys

    def remove_sample(self, sample: str):
        self.data["files"] = [f for f in self.data["files"] if f["sample"] != sample]
        self.data["samples"].pop(sample, None)
        for k in [k for k, s in self.spectra.items() if s.sample == sample]:
            self.spectra.pop(k)
            self.results.pop(k, None)
        self.save()

    def keys(self, region: str | None = None, sample: str | None = None, narrow_only=False) -> list[str]:
        out = []
        for k, s in self.spectra.items():
            if region and s.region != region:
                continue
            if sample and s.sample != sample:
                continue
            if narrow_only and s.is_survey:
                continue
            out.append(k)
        return out

    def samples(self) -> list[str]:
        return list(self.data.get("samples", {}))

    def regions(self) -> list[str]:
        seen = []
        for s in self.spectra.values():
            if s.region not in seen:
                seen.append(s.region)
        return seen

    def sample_label(self, sample: str) -> str:
        return self.data["samples"].get(sample, {}).get("label", sample)

    def set_sample_label(self, sample: str, label: str):
        self.data["samples"].setdefault(sample, {})["label"] = label
        self.save()

    # ------------------------------------------------------------------ charge correction
    def shift(self, sample: str) -> float:
        return float(self.data["samples"].get(sample, {}).get("shift", 0.0))

    def set_shift(self, sample: str, value: float, source: str = "manual"):
        d = self.data["samples"].setdefault(sample, {})
        d["shift"], d["shift_source"] = float(value), source
        self.save()

    def auto_charge(self, sample: str | None = None, ref: float | None = None) -> dict[str, float]:
        """C 1s C–C → ref (default project setting, 284.8 eV). Returns {sample: shift}; samples whose
        C 1s peak cannot be located reliably are skipped and listed in self.charge_failures."""
        ref = float(ref if ref is not None else self.settings.get("charge_ref", 284.8))
        out = {}
        self.charge_failures: dict[str, str] = {}
        for smp in ([sample] if sample else self.samples()):
            ks = self.keys("C 1s", smp)
            if not ks:
                continue
            s = self.spectra[ks[0]]
            try:
                c = quant.find_c1s_reference(s.be, s.cps)
            except ValueError as e:
                self.charge_failures[smp] = str(e)      # shift left unchanged
                continue
            out[smp] = round(ref - c, 3)
            d = self.data["samples"].setdefault(smp, {})
            d["shift"], d["shift_source"] = out[smp], f"C 1s {c:.2f} → {ref:.2f}"
        self.save()
        return out

    # ------------------------------------------------------------------ models
    def _model_path(self, key: str) -> str:
        return os.path.join(self.root, "models", safe_name(key) + ".json")

    def get_model(self, key: str) -> RegionModel | None:
        p = self._model_path(key)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return RegionModel.from_json(json.load(f)["model"])

    def get_model_record(self, key: str) -> dict | None:
        p = self._model_path(key)
        if not os.path.exists(p):
            return None
        with open(p, encoding="utf-8") as f:
            return json.load(f)

    def set_model(self, key: str, model: RegionModel, result: FitResult | None = None):
        os.makedirs(os.path.join(self.root, "models"), exist_ok=True)
        rec = dict(key=key, updated=_now(), model=model.to_json())
        if result is not None:
            rec["result"] = _jsonable(result.to_json(model))
        elif os.path.exists(self._model_path(key)):
            old = self.get_model_record(key) or {}
            if "result" in old:
                rec["result"] = old["result"]
                rec["result_stale"] = True
        tmp = self._model_path(key) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(rec, f, ensure_ascii=False, indent=1)
        os.replace(tmp, self._model_path(key))

    def delete_model(self, key: str):
        p = self._model_path(key)
        if os.path.exists(p):
            os.remove(p)
        self.results.pop(key, None)

    def new_model(self, key: str, preset_id: str | None = None, n_peaks: int | None = None) -> RegionModel:
        """preset_id: a preset id, '__generic__' (automatic peak finding for any element), or None
        (first preset for the region, else generic)."""
        s = self.spectra[key]
        sh = self.shift(s.sample)
        if preset_id == "__generic__":
            return presets.generic_model(s, sh, n_peaks)
        if preset_id:
            m = presets.model_from_preset(preset_id, s, sh, project_dir=self.root)
        else:
            cands = presets.presets_for(s.region, self.root)
            m = (presets.model_from_preset(cands[0], s, sh, project_dir=self.root) if cands
                 else presets.generic_model(s, sh, n_peaks))
        return m

    def prepared(self, key: str, model: RegionModel):
        s = self.spectra[key]
        return prepare(s.be, s.cps, model, self.shift(s.sample), acq_time=s.acq_time())

    def fit(self, key: str, model: RegionModel | None = None, n_starts: int = 3,
            save: bool = True) -> tuple[RegionModel, FitResult]:
        model = model or self.get_model(key) or self.new_model(key)
        errs = model.validate()
        if errs:
            raise ValueError("; ".join(errs))
        res = fit(model, self.prepared(key, model), n_starts=n_starts)
        apply_result(model, res)
        self.results[key] = res
        if save:
            self.set_model(key, model, res)
        return model, res

    def evaluate(self, key: str, model: RegionModel | None = None) -> FitResult | None:
        model = model or self.get_model(key)
        if model is None:
            return None
        return fit(model, self.prepared(key, model), optimize=False)

    def result(self, key: str) -> FitResult | None:
        """Last fit result (in memory) or a re-evaluation of the stored model."""
        return self.results.get(key) or self.evaluate(key)

    # ------------------------------------------------------------------ batch
    def batch_apply(self, source_key: str, target_keys: list[str], fix: tuple[str, ...] = (),
                    n_starts: int = 3) -> list[dict]:
        """Copy the model of source_key to targets and fit. fix: parameter names to freeze at the
        source values, e.g. ('fwhm', 'eta', 'alpha', 'gamma') or ('center',)."""
        src = self.get_model(source_key)
        if src is None:
            raise ValueError(f"No model for {source_key}")
        rows = []
        for k in target_keys:
            if k == source_key:
                continue
            m = src.copy()
            for _key, c, pn, p in m.param_items():
                if pn in fix and not p.expr:
                    p.vary = False
            s = self.spectra[k]
            presets.scale_areas(m, s, self.shift(s.sample))
            m2, r = self.fit(k, m, n_starts=n_starts)
            rows.append(dict(key=k, rms_pct=r.rms_pct, fractions=r.fractions, bound_hits=r.bound_hits))
        return rows

    # ------------------------------------------------------------------ quantification
    def rsf(self, region: str) -> float | None:
        user = self.settings.get("rsf", {})
        if region in user:
            return float(user[region])
        o = presets.orbital(region)
        return o.get("rsf") if o else None

    def set_rsf(self, region: str, value: float):
        self.settings.setdefault("rsf", {})[region] = float(value)
        self.save()

    def quantify(self, samples: list[str] | None = None, use_fit: bool = True) -> list[dict]:
        entries = []
        for smp in samples or self.samples():
            for k in self.keys(sample=smp, narrow_only=True):
                s = self.spectra[k]
                if s.region == "Survey":
                    continue
                area = None
                src = "raw"
                m = self.get_model(k) if use_fit else None
                if m is not None:
                    r = self.result(k)
                    if r is not None:
                        area = float(sum(r.areas[c.name] for c in m.components if c.in_total))
                        src = "fit"
                if area is None:
                    area = quant.raw_area(s.be, s.cps)
                entries.append(dict(sample=smp, region=s.region, key=k, area=area, area_source=src,
                                    rsf=self.rsf(s.region)))
        return quant.atomic_percent(entries) + [dict(e, at_pct=None) for e in entries if not e.get("rsf")]

    # ------------------------------------------------------------------ summary
    def summary(self) -> dict:
        out = dict(name=self.name, path=self.path, settings=self.settings, samples={}, spectra=[])
        for smp, d in self.data["samples"].items():
            out["samples"][smp] = dict(label=d.get("label", smp), shift=d.get("shift", 0.0),
                                       shift_source=d.get("shift_source", ""))
        for k, s in self.spectra.items():
            rec = self.get_model_record(k)
            item = dict(key=k, sample=s.sample, region=s.region, npts=len(s.be),
                        be_range=[round(float(s.be.min()), 2), round(float(s.be.max()), 2)],
                        has_model=rec is not None)
            if rec and "result" in rec:
                item["rms_pct"] = rec["result"].get("rms_pct")
                item["fractions"] = rec["result"].get("fractions")
                item["stale"] = rec.get("result_stale", False)
            out["spectra"].append(item)
        return out


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        v = float(o)
        return v if np.isfinite(v) else None
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, np.ndarray):
        return _jsonable(o.tolist())
    return o
