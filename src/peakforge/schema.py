"""Validation of project files, peak-model JSON, presets and column templates.

Grading (same rule as XAFSmith):
  error    the program would crash or silently compute something wrong
           (unknown parameter or shape, min > max, expression referring to a missing peak,
           circular expressions, fit range outside the data, ...)
  warning  it runs but is unusual or possibly unphysical
           (initial value outside its bounds, spin–orbit area ratio fixed away from (2j+1)
           theory, many free parameters per data point, background end outside the fit range, ...)

Each item says where it is: file name and field path, e.g. ``models/S1_Ir_4f.json: components[1]
(Ir4).params.fwhm``. ``python -m peakforge validate <project>`` prints the report; the GUI, CLI and
MCP server call it when a project or model is loaded (models with errors are refused).
"""
from __future__ import annotations

import json
import math
import os
import re

from .core import background as _bg
from .core import lineshapes
from .core.model import _REF, RegionModel, _parse

ERROR, WARNING = "error", "warning"
BASE_PARAMS = ("center", "fwhm", "area")
DOUBLET_PARAMS = ("split", "ratio")
WEIGHTINGS = ("none", "poisson")
_DEFAULT_MIN = {"area": 0.0, "fwhm": 0.05}
_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class SchemaError(ValueError):
    """A model / preset / project with validation errors; ``.report`` holds the details."""

    def __init__(self, report: "Report"):
        self.report = report
        super().__init__(report.text(errors_only=True))


class Report:
    def __init__(self):
        self.items: list[tuple[str, str, str]] = []     # (level, where, message)

    def err(self, where: str, msg: str):
        self.items.append((ERROR, where, msg))

    def warn(self, where: str, msg: str):
        self.items.append((WARNING, where, msg))

    def extend(self, other: "Report"):
        self.items.extend(other.items)

    @property
    def n_err(self) -> int:
        return sum(1 for i in self.items if i[0] == ERROR)

    @property
    def n_warn(self) -> int:
        return sum(1 for i in self.items if i[0] == WARNING)

    @property
    def ok(self) -> bool:
        return self.n_err == 0

    def errors(self) -> list[str]:
        return [f"{w}: {m}" for lv, w, m in self.items if lv == ERROR]

    def warnings(self) -> list[str]:
        return [f"{w}: {m}" for lv, w, m in self.items if lv == WARNING]

    def to_list(self) -> list[dict]:
        return [dict(level=lv, where=w, message=m) for lv, w, m in self.items]

    def text(self, errors_only: bool = False) -> str:
        rows = [f"{lv.upper():8s} {w}: {m}" for lv, w, m in self.items if not errors_only or lv == ERROR]
        return "\n".join(rows) if rows else "OK"

    def raise_if_errors(self):
        if self.n_err:
            raise SchemaError(self)


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _json_error(path: str, e: json.JSONDecodeError) -> str:
    return f"{os.path.basename(path)}: not valid JSON (line {e.lineno}, column {e.colno}: {e.msg})"


def load_json(path: str, rep: Report) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
    except json.JSONDecodeError as e:
        rep.err(os.path.basename(path), _json_error(path, e).split(": ", 1)[1])
        return None
    except UnicodeDecodeError as e:
        rep.err(os.path.basename(path), f"not UTF-8 text ({e.reason} at byte {e.start})")
        return None
    except OSError as e:
        rep.err(os.path.basename(path), f"cannot read: {e}")
        return None
    if not isinstance(d, dict):
        rep.err(os.path.basename(path), "top level must be a JSON object")
        return None
    return d


# ---------------------------------------------------------------------------- parameters
def _param(spec, where: str, rep: Report) -> dict | None:
    """Normalise one parameter spec to {value, min, max, vary, expr}; report malformed ones."""
    if _num(spec):
        return dict(value=float(spec), min=-math.inf, max=math.inf, vary=True, expr=None)
    if isinstance(spec, str):
        return dict(value=0.0, min=-math.inf, max=math.inf, vary=True, expr=spec)
    if isinstance(spec, list):
        if len(spec) == 1 and _num(spec[0]):
            return dict(value=float(spec[0]), min=-math.inf, max=math.inf, vary=False, expr=None)
        if len(spec) == 3 and all(_num(v) for v in spec):
            return dict(value=float(spec[0]), min=float(spec[1]), max=float(spec[2]), vary=True, expr=None)
        rep.err(where, f"list form must be [value] or [value, min, max], got {spec!r}")
        return None
    if isinstance(spec, dict):
        unknown = set(spec) - {"value", "min", "max", "vary", "expr"}
        if unknown:
            rep.err(where, f"unknown keys {sorted(unknown)} (allowed: value, min, max, vary, expr)")
        for k in ("value", "min", "max"):
            if k in spec and spec[k] is not None and not _num(spec[k]):
                rep.err(where, f"'{k}' must be a number, got {spec[k]!r}")
                return None
        if "vary" in spec and not isinstance(spec["vary"], bool):
            rep.err(where, f"'vary' must be true/false, got {spec['vary']!r}")
        expr = spec.get("expr") or None
        if expr is not None and not isinstance(expr, str):
            rep.err(where, f"'expr' must be a string, got {expr!r}")
            expr = None
        return dict(value=float(spec.get("value", 0.0) or 0.0),
                    min=-math.inf if spec.get("min") is None else float(spec["min"]),
                    max=math.inf if spec.get("max") is None else float(spec["max"]),
                    vary=bool(spec.get("vary", True)), expr=expr)
    rep.err(where, f"parameter must be a number, [value, min, max], an object or an expression, got {spec!r}")
    return None


def _cycles(deps: dict[str, set[str]]) -> list[list[str]]:
    """Cycles in the expression dependency graph {param: {params it uses}}."""
    out, state, stack = [], {}, []

    def visit(n):
        state[n] = 1
        stack.append(n)
        for m in sorted(deps.get(n, ())):
            if state.get(m) == 1:
                cyc = stack[stack.index(m):] + [m]
                if sorted(cyc[:-1]) not in [sorted(c[:-1]) for c in out]:
                    out.append(cyc)
            elif m in deps and not state.get(m):
                visit(m)
        stack.pop()
        state[n] = 2

    for n in sorted(deps):
        if not state.get(n):
            visit(n)
    return out


# ---------------------------------------------------------------------------- model
def check_model(d, where: str = "model", spectrum=None, shift: float = 0.0, rep: Report | None = None,
                preset: bool = False) -> Report:
    """Check a RegionModel JSON dict (or a preset, whose fit range is called 'range').
    ``spectrum``: the Spectrum the model is for (enables data-range checks)."""
    rep = rep if rep is not None else Report()
    if not isinstance(d, dict):
        rep.err(where, "model must be a JSON object")
        return rep
    comps = d.get("components", [])
    if not isinstance(comps, list):
        rep.err(f"{where}.components", "must be a list")
        return rep
    names: dict[str, dict] = {}          # component name -> normalised params
    exprs: dict[str, str] = {}
    extras: list[tuple] = []             # user-defined parameters (not part of the line shape)
    n_free = 0
    from . import presets as _presets
    orb = _presets.orbital(d.get("region", "")) if d.get("region") else None
    for i, c in enumerate(comps):
        cw = f"{where}.components[{i}]"
        if not isinstance(c, dict):
            rep.err(cw, "component must be an object")
            continue
        name = c.get("name")
        cw = f"{cw} ({name})" if name else cw
        if not isinstance(name, str) or not _NAME.match(name):
            rep.err(cw, f"name {name!r} must be an identifier (letters, digits, _; not starting with a digit)")
            continue
        if name in names:
            rep.err(cw, f"duplicate component name '{name}'")
            continue
        shape = c.get("shape", "gl")
        if shape not in lineshapes.SHAPES:
            rep.err(f"{cw}.shape", f"unknown line shape '{shape}' (known: {', '.join(lineshapes.SHAPES)})")
            continue
        doublet = bool(c.get("doublet", False))
        allowed = set(BASE_PARAMS) | set(lineshapes.SHAPES[shape]["extra"]) | (set(DOUBLET_PARAMS) if doublet else set())
        params = c.get("params", {})
        if not isinstance(params, dict):
            rep.err(f"{cw}.params", "must be an object")
            continue
        norm = {}
        for k, spec in params.items():
            pw = f"{cw}.params.{k}"
            if k not in allowed:
                if k in DOUBLET_PARAMS:
                    rep.err(pw, f"'{k}' needs \"doublet\": true")
                    continue
                if not _NAME.match(k):
                    rep.err(pw, f"parameter name '{k}' must be an identifier")
                    continue
                extras.append((pw, f"{name}.{k}", shape, allowed))     # auxiliary: must be used in an expression
            p = _param(spec, pw, rep)
            if p is None:
                continue
            norm[k] = p
            if p["expr"]:
                exprs[f"{name}.{k}"] = p["expr"]
                continue
            if k in _DEFAULT_MIN and p["min"] == -math.inf:
                p["min"] = _DEFAULT_MIN[k]              # same defaults as core.model.Component
            lo, hi, v = p["min"], p["max"], p["value"]
            if lo > hi:
                rep.err(pw, f"min {lo:g} > max {hi:g}")
            elif lo == hi and p["vary"]:
                rep.err(pw, f"min = max = {lo:g} but the parameter is free (set \"vary\": false)")
            elif p["vary"] and not (lo <= v <= hi):
                rep.warn(pw, f"start value {v:g} outside [{lo:g}, {hi:g}] (clipped at fit time)")
            if k in ("fwhm", "gamma") and hi <= 0:
                rep.err(pw, f"{k} must be allowed to be > 0 (max {hi:g})")
            if k == "fwhm" and p["vary"] and lo <= 0:
                rep.warn(pw, f"min {lo:g} ≤ 0: the fit may collapse the peak to zero width")
            if k == "area" and v < 0 and not p["vary"]:
                rep.warn(pw, f"fixed negative area {v:g}")
            if k == "ratio" and doublet and orb and orb.get("ratio") and not p["vary"]:
                th = float(orb["ratio"])
                if abs(v - th) > 0.05 * th + 1e-9:
                    rep.warn(pw, f"spin–orbit area ratio fixed at {v:g}; (2j+1) theory for {d.get('region')} "
                                 f"is {th:g}")
            if k == "split" and doublet and orb and orb.get("split") and not p["vary"]:
                th = float(orb["split"])
                if abs(v - th) > max(0.3, 0.1 * th):
                    rep.warn(pw, f"spin–orbit split fixed at {v:g} eV; tabulated value for {d.get('region')} "
                                 f"is {th:g} eV")
            if p["vary"]:
                n_free += 1
        names[name] = norm
        for k in ("in_total", "doublet"):
            if k in c and not isinstance(c[k], bool):
                rep.err(f"{cw}.{k}", f"must be true/false, got {c[k]!r}")
        if "sub_labels" in c and (not isinstance(c["sub_labels"], list) or len(c["sub_labels"]) != 2):
            rep.err(f"{cw}.sub_labels", "must be a list of two labels")
        unknown = set(c) - {"name", "label", "shape", "params", "doublet", "sub_labels", "in_total", "group", "color"}
        if unknown:
            rep.warn(cw, f"ignored keys {sorted(unknown)}")
    # expressions: syntax, references, cycles
    deps: dict[str, set[str]] = {}
    for key, ex in exprs.items():
        cn, pn = key.split(".", 1)
        idx = next(i for i, c in enumerate(comps) if isinstance(c, dict) and c.get("name") == cn)
        pw = f"{where}.components[{idx}] ({cn}).params.{pn}.expr"
        try:
            _parse(ex)
        except ValueError as e:
            rep.err(pw, str(e))
            continue
        refs = set()
        for rc, rp in _REF.findall(ex):
            if rc not in names:
                rep.err(pw, f"'{ex}' refers to unknown component '{rc}' (components: {', '.join(names)})")
            elif rp not in names[rc] and rp not in _defaults(comps, rc):
                rep.err(pw, f"'{ex}': component '{rc}' has no parameter '{rp}'")
            else:
                refs.add(f"{rc}.{rp}")
        deps[key] = refs
    for cyc in _cycles(deps):
        rep.err(f"{where}.components", "circular expressions: " + " → ".join(cyc))
    used = set().union(*deps.values()) if deps else set()
    for pw, full, shape, allowed in extras:
        cn, k = full.split(".", 1)
        p = names.get(cn, {}).get(k)
        if full in used or p is None:
            continue
        if p["vary"] and not p["expr"]:
            rep.err(pw, f"free parameter not used by the '{shape}' line shape nor by any expression "
                        f"(a typo? shape parameters: {', '.join(sorted(allowed))}) — the fit cannot determine it")
        else:
            rep.warn(pw, "not used by the line shape nor by any expression (ignored)")
    # background
    bgd = d.get("background") or {}
    if not isinstance(bgd, dict):
        rep.err(f"{where}.background", "must be an object")
        bgd = {}
    kind = bgd.get("kind", "shirley")
    if kind not in _bg.KINDS:
        rep.err(f"{where}.background.kind", f"unknown background '{kind}' (known: {', '.join(_bg.KINDS)})")
    blo, bhi = bgd.get("lo"), bgd.get("hi")
    for k, v in (("lo", blo), ("hi", bhi), ("avg", bgd.get("avg"))):
        if v is not None and not _num(v):
            rep.err(f"{where}.background.{k}", f"must be a number or null, got {v!r}")
    if _num(blo) and _num(bhi) and blo >= bhi:
        rep.err(f"{where}.background", f"lo {blo:g} ≥ hi {bhi:g}")
    if _num(bgd.get("avg")) and bgd["avg"] < 0:
        rep.err(f"{where}.background.avg", "must be ≥ 0")
    t = bgd.get("tougaard")
    if t is not None and (not isinstance(t, list) or len(t) not in (2, 3) or not all(_num(v) for v in t)):
        rep.err(f"{where}.background.tougaard", f"must be [B, C] or [B, C, D], got {t!r}")
    # fit range
    rkey = "range" if preset else "fit_range"
    fr = d.get(rkey)
    rng = None
    if fr is not None:
        if not isinstance(fr, list) or len(fr) != 2 or not all(_num(v) for v in fr):
            rep.err(f"{where}.{rkey}", f"must be [low, high] in eV or null, got {fr!r}")
        elif fr[0] == fr[1]:
            rep.err(f"{where}.{rkey}", "has zero width")
        else:
            rng = sorted(float(v) for v in fr)
            if _num(blo) and _num(bhi) and (blo < rng[0] - 1e-6 or bhi > rng[1] + 1e-6):
                rep.warn(f"{where}.background", f"end points [{blo:g}, {bhi:g}] outside the fit range "
                                                f"[{rng[0]:g}, {rng[1]:g}]")
    w = d.get("weighting", "none")
    if w not in WEIGHTINGS:
        rep.err(f"{where}.weighting", f"must be one of {WEIGHTINGS}, got {w!r}")
    if spectrum is not None:
        import numpy as np
        x = spectrum.be + shift
        a, b = (rng if rng else (float(x.min()), float(x.max())))
        npts = int(((x >= a) & (x <= b)).sum())
        if rng and (rng[1] < x.min() or rng[0] > x.max()):
            rep.err(f"{where}.{rkey}", f"[{rng[0]:g}, {rng[1]:g}] eV does not overlap the data "
                                       f"[{x.min():.2f}, {x.max():.2f}] eV (charge shift {shift:+.2f} eV)")
        elif npts < 5:
            rep.err(f"{where}.{rkey}", f"only {npts} data points inside the fit range")
        elif comps and n_free > npts / 3:
            rep.warn(where, f"{n_free} free parameters for {npts} data points")
        for cn, ps in names.items():
            c = ps.get("center")
            if c and not c["expr"] and np.isfinite(c["value"]) and not (a - 5 <= c["value"] <= b + 5):
                rep.warn(f"{where} ({cn}).params.center", f"{c['value']:g} eV lies outside the fitted window "
                                                          f"[{a:.2f}, {b:.2f}] eV")
    return rep


def _defaults(comps, cname) -> set[str]:
    """Parameters a component always has even if not listed in the JSON (filled in by Component)."""
    c = next((c for c in comps if isinstance(c, dict) and c.get("name") == cname), {})
    shape = c.get("shape", "gl")
    out = set(BASE_PARAMS) | set(lineshapes.SHAPES.get(shape, {"extra": {}})["extra"])
    if c.get("doublet"):
        out |= set(DOUBLET_PARAMS)
    return out


def model_from_json_checked(d: dict, where: str = "model", spectrum=None, shift: float = 0.0) -> tuple[RegionModel, Report]:
    """Validate, then build. Raises SchemaError when there are errors."""
    rep = check_model(d, where, spectrum, shift)
    rep.raise_if_errors()
    return RegionModel.from_json(d), rep


# ---------------------------------------------------------------------------- preset / template
def check_preset(d, where: str) -> Report:
    rep = Report()
    if not isinstance(d, dict):
        rep.err(where, "preset must be a JSON object")
        return rep
    if not d.get("region"):
        rep.warn(where, "no 'region': the preset will not be offered for any spectrum")
    check_model(d, where, rep=rep, preset=True)
    return rep


def check_template(tpl, where: str) -> Report:
    from .io.table import check_template as _ct
    rep = Report()
    if not isinstance(tpl, dict):
        rep.err(where, "column template must be an object")
        return rep
    for e in _ct(tpl):
        rep.err(where, e)
    return rep


# ---------------------------------------------------------------------------- project
PROJECT_KEYS = {"format", "version", "name", "created", "modified", "settings", "files", "samples",
                "region_override", "formats"}


def check_project_data(data: dict, fname: str, root: str | None = None) -> Report:
    rep = Report()
    if data.get("format") != "peakforge-project":
        rep.err(f"{fname}.format", f"expected 'peakforge-project', got {data.get('format')!r}")
        return rep
    unknown = set(data) - PROJECT_KEYS
    if unknown:
        rep.warn(fname, f"unknown keys {sorted(unknown)} (kept but ignored)")
    files = data.get("files", [])
    if not isinstance(files, list):
        rep.err(f"{fname}.files", "must be a list")
        files = []
    samples = data.get("samples", {})
    if not isinstance(samples, dict):
        rep.err(f"{fname}.samples", "must be an object")
        samples = {}
    formats = data.get("formats", {}) or {}
    if not isinstance(formats, dict):
        rep.err(f"{fname}.formats", "must be an object {name: template}")
        formats = {}
    for name, tpl in formats.items():       # only the files using it fail → warning here; the read
        for lv, w, m in check_template(tpl, f"{fname}.formats.{name}").items:   # error is reported per file
            rep.warn(w, m + " (files using this template cannot be read)")
    seen = set()
    for i, f in enumerate(files):
        fw = f"{fname}.files[{i}]"
        if not isinstance(f, dict) or not isinstance(f.get("path"), str) or not f.get("sample"):
            rep.err(fw, "each file needs 'path' and 'sample'")
            continue
        fw = f"{fw} ({f['path']})"
        if f["path"] in seen:
            rep.warn(fw, "file listed twice")
        seen.add(f["path"])
        if root and not os.path.exists(os.path.join(root, f["path"])):
            rep.warn(fw, "file not found (its spectra are skipped)")
        if f.get("template") and f["template"] not in formats:
            rep.warn(f"{fw}.template", f"no column template named '{f['template']}' in 'formats' "
                                       "(the file cannot be read)")
        if f["sample"] not in samples:
            rep.warn(fw, f"sample '{f['sample']}' has no entry in 'samples' (charge shift 0)")
    for smp, sd in samples.items():
        if not isinstance(sd, dict):
            rep.err(f"{fname}.samples.{smp}", "must be an object")
            continue
        if "shift" in sd and not _num(sd["shift"]):
            rep.err(f"{fname}.samples.{smp}.shift", f"must be a number, got {sd['shift']!r}")
        elif _num(sd.get("shift")) and abs(sd["shift"]) > 15:
            rep.warn(f"{fname}.samples.{smp}.shift", f"charge shift {sd['shift']:+g} eV is unusually large")
    st = data.get("settings", {}) or {}
    if _num(st.get("charge_ref")) and not 280 < st["charge_ref"] < 290:
        rep.warn(f"{fname}.settings.charge_ref", f"{st['charge_ref']:g} eV is not a C 1s reference energy")
    ro = data.get("region_override", {}) or {}
    if not isinstance(ro, dict) or not all(isinstance(v, str) for v in ro.values()):
        rep.err(f"{fname}.region_override", "must map spectrum key -> region label")
    return rep


def validate_project(path: str, deep: bool = True) -> Report:
    """Full check of a project folder: project file, column templates, every model JSON (against its
    spectrum when the data can be read) and the project presets."""
    from .project import Project, find_project
    rep = Report()
    try:
        path = find_project(path)
    except FileNotFoundError as e:
        rep.err(os.path.basename(path), str(e))
        return rep
    fname = os.path.basename(path)
    data = load_json(path, rep)
    if data is None:
        return rep
    root = os.path.dirname(path)
    rep.extend(check_project_data(data, fname, root))
    if not rep.ok or not deep:
        return rep
    try:
        proj = Project(path, data)
    except Exception as e:      # noqa: BLE001 — report, don't crash the validator
        rep.err(fname, f"project cannot be opened: {e}")
        return rep
    for f in data.get("files", []):
        if isinstance(f, dict) and f.get("error"):
            rep.err(f"{fname}.files ({f['path']})", f"cannot be read: {f['error']}")
    mdir = os.path.join(root, "models")
    by_file = {os.path.basename(proj._model_path(k)): k for k in proj.spectra}
    for mf in sorted(os.listdir(mdir)) if os.path.isdir(mdir) else []:
        if not mf.endswith(".json"):
            continue
        where = f"models/{mf}"
        rec = load_json(os.path.join(mdir, mf), rep)
        if rec is None:
            continue
        if "model" not in rec:
            rep.err(where, "no 'model' entry")
            continue
        key = by_file.get(mf)
        sp = proj.spectra.get(key) if key else None
        if key is None:
            rep.warn(where, "no spectrum in the project matches this model file")
        check_model(rec["model"], where, sp, proj.shift(sp.sample) if sp else 0.0, rep=rep)
    pdir = os.path.join(root, "presets")
    for pf in sorted(os.listdir(pdir)) if os.path.isdir(pdir) else []:
        if pf.endswith(".json"):
            d = load_json(os.path.join(pdir, pf), rep)
            if d is not None:
                rep.extend(check_preset(d, f"presets/{pf}"))
    return rep
