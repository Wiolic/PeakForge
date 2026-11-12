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
import time

import numpy as np

from . import __version__, presets
from .core import quant
from .core.fit import FitResult, apply_result, fit, prepare
from .core.model import RegionModel
from .io import ReadError, read_file
from .logs import log
from .msg import Msg, exc_msg
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
        self.charge_warnings: dict[str, list[str]] = {}
        self.model_reports: dict = {}           # key -> schema.Report of the last get_model()
        self.validation = None                  # schema.Report from Project.open()
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
                    modified=_now(), settings=dict(charge_ref=284.8, lang="zh", theme="glacier", palette=dict(combo="glacier")),
                    files=[], samples={})
        p = cls(path, data)
        p.save()
        return p

    @classmethod
    def open(cls, path: str) -> "Project":
        path = find_project(path)
        from . import schema
        rep0 = schema.Report()
        data = schema.load_json(path, rep0)
        rep0.raise_if_errors()
        rep = schema.check_project_data(data, os.path.basename(path), os.path.dirname(path))
        if rep.items:
            log.warning("project %s: %s", path, rep.text())
        rep.raise_if_errors()
        p = cls(path, data)
        p.validation = rep
        return p

    def save(self):
        self.data["modified"] = _now()
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=1)
        # Windows: replacing fails while another handle (file watcher, antivirus, sync client) briefly has the
        # target open -> retry for up to ~1 s before giving up
        for i in range(20):
            try:
                os.replace(tmp, self.path)
                return
            except PermissionError:
                if i == 19:
                    raise
                log.info("project save: %s busy, retrying", self.path)
                time.sleep(0.05)

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
                sps = read_file(p, fmt=f.get("template"), templates=self.formats)
            except ReadError as e:
                f["error"] = str(e)
                log.warning("project %s: %s", self.path, e)
                continue
            f.pop("error", None)
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

    @property
    def formats(self) -> dict:
        """Column templates saved by the import wizard: {name: template} (see io/table.py)."""
        return self.data.setdefault("formats", {})

    def add_template(self, name: str, template: dict):
        from .io.wizard import add_template
        add_template(self.data, name, template)
        self.save()

    def add_file(self, src: str, sample: str | None = None, copy: bool = True,
                 template: str | None = None) -> list[str]:
        """template: name of a column template in self.formats (tables only)."""
        src = os.path.abspath(src)
        if template and template not in self.formats:
            raise ReadError(f"No column template '{template}' in this project",
                            f"工程中没有名为“{template}”的列映射模板")
        sps = read_file(src, fmt=template, templates=self.formats)     # validate before copying
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
                self._copy_companions(src, dst, sps[0].meta.get("reader", ""))
            rel = os.path.relpath(dst, self.root)
        else:
            rel = os.path.relpath(src, self.root)
        entry = dict(path=rel.replace("\\", "/"), sample=sample,
                     format=sps[0].meta.get("reader", ""), added=_now())
        if template:
            entry["template"] = template
        self.data["files"].append(entry)
        self.data["samples"].setdefault(sample, dict(shift=0.0, shift_source="none", label=sample))
        keys = []
        for s in sps:
            s.sample = sample
            self.spectra[s.key] = s
            keys.append(s.key)
        self.save()
        return keys

    @staticmethod
    def _copy_companions(src: str, dst: str, reader: str):
        """Files/folders the reader needs next to the data file (Avantage: <name>.vgp + <name>.DATA/),
        renamed like dst when dst got a numeric suffix."""
        from .io.registry import BY_NAME
        r = BY_NAME.get(reader)
        if r is None:
            return
        s_stem, d_stem = os.path.splitext(os.path.basename(src))[0], os.path.splitext(os.path.basename(dst))[0]
        for c in r.companions(src):
            name = os.path.basename(c)
            if name.lower().startswith(s_stem.lower()):
                name = d_stem + name[len(s_stem):]
            target = os.path.join(os.path.dirname(dst), name)
            if os.path.isdir(c):
                shutil.copytree(c, target, dirs_exist_ok=True)
            else:
                shutil.copy2(c, target)

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

    # ------------------------------------------------------------------ colours
    def palette(self) -> dict:
        """settings["palette"] (combo / assign / figures); projects of version <= 0.2 only have settings["theme"],
        which is mapped to the closest combo."""
        from .export.themes import legacy_palette
        pal = self.settings.get("palette")
        return pal if isinstance(pal, dict) else legacy_palette(self.settings.get("theme"))

    def figure_theme(self, key: str | None, n: int | None = None, region: str | None = None,
                     palette: dict | None = None) -> dict:
        """Colours of the figure `key` (resolve_theme with this project's palette). n = number of components
        (default: those of the stored model, else 8)."""
        from .export.themes import resolve_theme
        s = self.spectra.get(key) if key else None
        region = region or (s.region if s else "")
        if n is None:
            rec = self.get_model_record(key) if key else None
            n = len((rec or {}).get("model", {}).get("components", [])) or 8
        regs = [x.region for x in self.spectra.values() if not x.is_survey]
        return resolve_theme(self.palette() if palette is None else palette, key, region, regs, n)

    def set_palette(self, combo: str | None = None, reset: bool = False, save: bool = True) -> dict:
        """Choose the combo of the project; reset=True also drops all element / per-figure choices.
        Keeps settings["theme"] = combo for older readers."""
        from .export.themes import theme_id
        pal = dict(self.palette())
        if combo is not None:
            pal["combo"] = theme_id(combo)
        if reset:
            pal.pop("assign", None)
            pal.pop("figures", None)
            pal.pop("mode", None)
        self.settings["palette"] = pal
        self.settings["theme"] = pal["combo"]
        if save:
            self.save()
        return pal

    def set_figure_color(self, key: str, base: str | None = None, mode: str | None = None,
                         colors: list[str] | None = None, save: bool = True):
        """Per-figure override; all None removes it (back to the combo)."""
        pal = dict(self.palette())
        figs = dict(pal.get("figures") or {})
        d = {k: v for k, v in (("base", base), ("mode", mode), ("colors", colors)) if v}
        if d:
            figs[key] = d
        else:
            figs.pop(key, None)
        pal["figures"] = figs
        self.settings["palette"] = pal
        if save:
            self.save()

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

    def auto_charge(self, sample: str | None = None, ref: float | None = None, force: bool = False,
                    region: str | None = None) -> dict[str, float]:
        """Reference line (project setting charge_region, default C 1s C–C) → ref (charge_ref, default
        284.8 eV), see quant.find_reference. Returns {sample: shift}. Samples without a usable peak, or
        whose result has low confidence (unless force=True), keep their shift and are listed in
        self.charge_failures with the reason (and the proposed shift). Optional internal-consistency
        checks (settings charge_checks = [{region, be, tol}]) add messages to self.charge_warnings."""
        region = region or self.settings.get("charge_region") or "C 1s"
        ref = self.charge_reference(region, ref)
        out = {}
        self.charge_failures: dict[str, str] = {}
        self.charge_warnings: dict[str, list[str]] = {}
        for smp in ([sample] if sample else self.samples()):
            ks = self.keys(region, smp)
            if not ks:
                continue
            s = self.spectra[ks[0]]
            try:
                r = quant.find_reference(s.be, s.cps, ref, fluoro_check=region == "C 1s")
            except ValueError as e:
                self.charge_failures[smp] = exc_msg(e)      # shift left unchanged
                continue
            shift = round(ref - r.position, 3)
            if r.confidence != "high" and not force:
                self.charge_failures[smp] = Msg(f"{region} {r.position:.2f} eV → proposed shift {shift:+.2f} eV, "
                                                "not applied: " + "; ".join(r.reasons), "charge_not_applied",
                                                region=region, x=f"{r.position:.2f}", shift=f"{shift:+.2f}",
                                                reasons=list(r.reasons))
                continue
            out[smp] = shift
            d = self.data["samples"].setdefault(smp, {})
            d["shift"], d["shift_source"] = shift, f"{region} {r.position:.2f} → {ref:.2f}"
            if r.reasons:
                d["shift_source"] += " (forced: " + "; ".join(r.reasons) + ")"
            notes = list(r.notes)
            if region == "C 1s" and not notes:
                notes += self._fluorine_note(smp, shift)
            if notes:
                self.charge_warnings.setdefault(smp, []).extend(notes)
            self._charge_checks(smp, shift)
        self.save()
        return out

    def charge_reference(self, region: str | None, ref: float | None) -> float:
        """Reference energy for `region`: explicit `ref`; else the project's charge_ref when `region` is the
        project's charge_region; else 284.8 eV for C 1s. Any other region needs an explicit energy (the stored
        value belongs to a different line)."""
        own = self.settings.get("charge_region") or "C 1s"
        region = region or own
        if ref is not None:
            return float(ref)
        if region == own:
            return float(self.settings.get("charge_ref", 284.8))
        if region == "C 1s":
            return 284.8
        raise ValueError(f"reference energy for {region} not given (the project setting {own} / "
                         f"{self.settings.get('charge_ref', 284.8)} eV belongs to another line) — pass ref")

    def _fluorine_note(self, smp: str, shift: float) -> list[str]:
        """F 1s in the sample (narrow scan, else survey): a fluoropolymer binder/membrane (e.g. Nafion) may
        charge differently from the active material even when its CF₂ line is outside the C 1s window.
        The ±6 eV search around 688 eV only detects F 1s; it does not identify the compound."""
        for k in self.keys("F 1s", smp) + [k for k in self.keys(sample=smp) if self.spectra[k].is_survey]:
            s = self.spectra[k]
            try:
                q = quant.find_reference(s.be, s.cps, 688.0 - shift)
            except ValueError:
                continue
            if q.snr >= 10:
                return [Msg(f"F 1s present ({q.position + shift:.1f} eV after correction, {s.region}): if it is a "
                            "fluoropolymer (e.g. Nafion), the insulating phase may charge differently from the "
                            "active material — check against an internal reference before trusting the shift",
                            "charge_f1s", x=f"{q.position + shift:.1f}", region=s.region)]
        return []

    def _charge_checks(self, smp: str, shift: float):
        for chk in self.settings.get("charge_checks") or []:
            ks = self.keys(chk.get("region", ""), smp)
            if not ks:
                continue
            s = self.spectra[ks[0]]
            be, tol = float(chk["be"]), float(chk.get("tol", 0.3))
            try:
                q = quant.find_reference(s.be, s.cps, be - shift, span=(-2.0, 2.0))
            except ValueError as e:
                err = exc_msg(e)
                self.charge_warnings.setdefault(smp, []).append(
                    Msg(f"{chk['region']}: {err}", "charge_check_error", region=chk["region"], err=err))
                continue
            got = q.position + shift
            if abs(got - be) > tol:
                self.charge_warnings.setdefault(smp, []).append(Msg(
                    f"{chk['region']} lowest-BE peak at {got:.2f} eV after correction, expected {be:.2f} ± {tol:.2f} eV",
                    "charge_check_off", region=chk["region"], x=f"{got:.2f}", be=f"{be:.2f}", tol=f"{tol:.2f}"))

    # ------------------------------------------------------------------ models
    def _model_path(self, key: str) -> str:
        return os.path.join(self.root, "models", safe_name(key) + ".json")

    def get_model(self, key: str) -> RegionModel | None:
        """The saved model, validated against its spectrum (schema.py). Raises SchemaError when the
        file would crash the fit or compute something wrong; warnings go to self.model_reports[key]."""
        from . import schema
        p = self._model_path(key)
        if not os.path.exists(p):
            return None
        where = f"models/{os.path.basename(p)}"
        rep = schema.Report()
        rec = schema.load_json(p, rep)
        if rec is not None and "model" not in rec:
            rep.err(where, "no 'model' entry")
        if rec is not None and "model" in rec:
            s = self.spectra.get(key)
            schema.check_model(rec["model"], where, s, self.shift(s.sample) if s else 0.0, rep=rep)
        self.model_reports[key] = rep
        if not rep.ok:
            log.warning("invalid model file %s: %s", p, rep.text())
        rep.raise_if_errors()
        return RegionModel.from_json(rec["model"])

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
        return build_model(s, self.shift(s.sample), self.root, preset_id, n_peaks)

    def prepared(self, key: str, model: RegionModel):
        s = self.spectra[key]
        return prepare_for(s, self.shift(s.sample), model)

    def fit_inputs(self, key: str, model: RegionModel | None = None):
        """(model, prepared data) for a fit of `key`; validates the model. Reads the project only, so the GUI
        calls it in the UI thread and runs core.fit.fit on the result in a worker (the model is not copied:
        pass model.copy() when the worker must not share it)."""
        model = model or self.get_model(key) or self.new_model(key)
        errs = model.validate()
        if errs:
            raise ValueError("; ".join(errs))
        return model, self.prepared(key, model)

    def overlap_flags(self, key: str, model: RegionModel | None = None) -> list[dict]:
        """Quality flags for other core levels (of elements measured in the same sample) that can lie in
        the fit window of `key` (presets.overlapping_levels)."""
        s = self.spectra[key]
        if s.is_survey:
            return []
        els = {t.element for t in self.spectra.values() if t.sample == s.sample and t.element and not t.is_survey}
        if s.element:
            els.add(s.element)
        sh = self.shift(s.sample)
        lo, hi = (sorted(model.fit_range) if model is not None and model.fit_range
                  else (float(s.be.min()) + sh, float(s.be.max()) + sh))
        return [dict(level="warning", code="overlap",
                     args=dict(level=h["level"], be=f"{h['be']:g}", lines=", ".join(f"{e:g}" for e in h["lines"]),
                               shift=f"{presets.OVERLAP_SHIFT:g}"),
                     text=f"{h['level']} (table ≈ {h['be']:g} eV; lines near {', '.join(f'{e:g}' for e in h['lines'])} eV, "
                          f"up to +{presets.OVERLAP_SHIFT:g} eV in compounds) can lie in this window — include it "
                          "in the model or check that it is negligible")
                for h in presets.overlapping_levels(s.region, els, lo, hi)]

    def _add_overlaps(self, key: str, model: RegionModel, res: FitResult) -> FitResult:
        if res is not None and not any(f.get("code") == "overlap" for f in res.flags):
            res.flags = list(res.flags) + self.overlap_flags(key, model)
        return res

    def store_fit(self, key: str, model: RegionModel, res: FitResult, save: bool = True):
        """Record a finished fit (model already updated with apply_result)."""
        self._add_overlaps(key, model, res)
        self.results[key] = res
        if save:
            self.set_model(key, model, res)

    def fit(self, key: str, model: RegionModel | None = None, n_starts: int = 3,
            save: bool = True) -> tuple[RegionModel, FitResult]:
        model, prep = self.fit_inputs(key, model)
        res = fit(model, prep, n_starts=n_starts)
        apply_result(model, res)
        self.store_fit(key, model, res, save)
        return model, res

    def evaluate(self, key: str, model: RegionModel | None = None) -> FitResult | None:
        model = model or self.get_model(key)
        if model is None:
            return None
        return self._add_overlaps(key, model, fit(model, self.prepared(key, model), optimize=False))

    def result(self, key: str) -> FitResult | None:
        """Last fit result (in memory) or a re-evaluation of the stored model."""
        return self.results.get(key) or self.evaluate(key)

    # ------------------------------------------------------------------ batch
    def batch_model(self, src: RegionModel, key: str, fix: tuple[str, ...]) -> RegionModel:
        """Copy of `src` for spectrum `key`: `fix` parameters frozen, areas rescaled to the target."""
        m = src.copy()
        for _key, c, pn, p in m.param_items():
            if pn in fix and not p.expr:
                p.vary = False
        s = self.spectra[key]
        presets.scale_areas(m, s, self.shift(s.sample))
        return m

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
            m2, r = self.fit(k, self.batch_model(src, k, fix), n_starts=n_starts)
            rows.append(dict(key=k, rms_pct=r.rms_pct, fractions=r.fractions, bound_hits=r.bound_hits))
        return rows

    # ------------------------------------------------------------------ quantification
    def rsf(self, region: str) -> float | None:
        user = self.settings.get("rsf", {})
        if region in user:
            return float(user[region])
        o = presets.orbital(region)
        return o.get("rsf") if o else None

    def rsf_for(self, key: str) -> float | None:
        """RSF for one spectrum: a user value for its region wins; otherwise the level's tabulated RSF,
        scaled down when the scan holds only one j sub-level (presets.subshell_fraction)."""
        s = self.spectra[key]
        user = self.settings.get("rsf", {})
        if s.region in user:
            return float(user[s.region])
        o = presets.orbital(s.region)
        if not o or not o.get("rsf"):
            return None
        return float(o["rsf"]) * presets.subshell_fraction(s)

    def set_rsf(self, region: str, value: float):
        self.settings.setdefault("rsf", {})[region] = float(value)
        self.save()

    def quantify(self, samples: list[str] | None = None, use_fit: bool = True,
                 results: dict | None = None) -> list[dict]:
        """results: optional {key: FitResult} the caller already evaluated (avoids evaluating twice)."""
        entries = []
        for smp in samples or self.samples():
            for k in self.keys(sample=smp, narrow_only=True):
                s = self.spectra[k]
                if s.region == "Survey":
                    continue
                area = None
                src = "raw"
                try:
                    m = self.get_model(k) if use_fit else None
                except ValueError as e:     # SchemaError: fall back to the raw area for this spectrum
                    log.warning("quantify: model of %s ignored: %s", k, e)
                    m, src = None, "raw (model invalid)"
                if m is not None:
                    r = (results or {}).get(k) or self.result(k)
                    if r is not None:
                        area = float(sum(r.areas[c.name] for c in m.components if c.in_total))
                        src = "fit"
                rsf = self.rsf_for(k)
                if area is None:
                    area = quant.raw_area(s.be, s.cps)
                elif (rsf and presets.high_j_only(m) and presets.subshell_fraction(s) == 1.0
                      and s.region not in self.settings.get("rsf", {})):
                    r_ = (presets.orbital(f"{s.element} {(presets.orbital(s.region) or {}).get('level')}") or {}).get("ratio")
                    if r_:
                        rsf *= 1.0 / (1.0 + r_)      # fit covers the high-j line only (multiplet table)
                        src += " (high-j)"
                entries.append(dict(sample=smp, region=s.region, key=k, area=area, area_source=src,
                                    rsf=rsf))
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


def build_model(s, sh: float, root: str, preset_id: str | None = None, n_peaks: int | None = None) -> RegionModel:
    """New model for spectrum `s` at charge shift `sh` (Project.new_model without the Project, so a worker
    thread can build it from a spectrum reference taken in the UI thread)."""
    if preset_id == "__generic__":
        return presets.generic_model(s, sh, n_peaks)
    if preset_id:
        return presets.model_from_preset(preset_id, s, sh, project_dir=root)
    cands = [p for p in presets.presets_for(s.region, root) if p.get("auto", True)]
    return (presets.model_from_preset(cands[0], s, sh, project_dir=root) if cands
            else presets.generic_model(s, sh, n_peaks))


def prepare_for(s, sh: float, model: RegionModel):
    """Prepared data of spectrum `s` for `model` (Project.prepared without the Project)."""
    return prepare(s.be, s.cps, model, sh, acq_time=s.acq_time())


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
