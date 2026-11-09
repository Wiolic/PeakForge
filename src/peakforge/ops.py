"""High-level operations shared by the CLI, the MCP server and the GUI command box.
Every function takes a Project and returns plain JSON-serialisable data."""
from __future__ import annotations

import json

from . import presets
from .core.diagnostics import diagnose
from .core.model import Component, Param, RegionModel
from .project import Project, _jsonable


def resolve_key(p: Project, key: str) -> str:
    """Accept the exact key, or 'sample/region', or a unique substring."""
    if key in p.spectra:
        return key
    c = [k for k in p.spectra if key.lower() in k.lower()]
    if len(c) == 1:
        return c[0]
    if not c:
        raise KeyError(f"No spectrum matches '{key}'. Available: {list(p.spectra)}")
    raise KeyError(f"'{key}' is ambiguous: {c}")


def keys_for(p: Project, keys=None, region=None, sample=None) -> list[str]:
    if keys:
        return [resolve_key(p, k) for k in keys]
    return p.keys(region=region, sample=sample, narrow_only=True)


def list_presets(p: Project | None = None, region: str | None = None) -> list[dict]:
    out = []
    for pid, d in presets.list_presets(p.root if p else None).items():
        if region and d.get("region") != region:
            continue
        out.append(dict(id=pid, region=d.get("region"), name_en=d.get("name_en"), name_zh=d.get("name_zh"),
                        note_en=d.get("note_en", ""), builtin=d.get("_builtin", False),
                        components=[c["name"] for c in d.get("components", [])]))
    return out


def set_region(p: Project, key: str, region: str) -> dict:
    """Assign element / core level (e.g. 'Fe 2p', 'Fe 2p3/2', 'Ce 3d') to a spectrum."""
    key = resolve_key(p, key)
    new = p.set_region(key, region)
    from . import presets
    return dict(old_key=key, key=new, orbital=presets.orbital(p.spectra[new].region))


def list_orbitals(element: str | None = None) -> list[dict]:
    from . import presets
    return [dict(region=k, **v) for k, v in presets.orbitals().items() if not element or v["element"] == element]


def model_json(p: Project, key: str) -> dict:
    key = resolve_key(p, key)
    rec = p.get_model_record(key)
    if rec is None:
        return dict(key=key, model=None)
    return _jsonable(rec)


def set_model(p: Project, key: str, model: dict | str) -> dict:
    key = resolve_key(p, key)
    if isinstance(model, str):
        model = json.loads(model)
    m = RegionModel.from_json(model)
    if not m.region:
        m.region = p.spectra[key].region
    errs = m.validate()
    if errs:
        raise ValueError("; ".join(errs))
    p.set_model(key, m)
    return dict(key=key, ok=True, components=m.names())


def apply_preset(p: Project, key: str, preset_id: str | None = None) -> dict:
    key = resolve_key(p, key)
    m = p.new_model(key, preset_id)
    p.set_model(key, m)
    return dict(key=key, preset=m.preset, components=m.names(), fit_range=m.fit_range,
                background=m.background.to_json())


def add_component(p: Project, key: str, name: str | None = None, center: float = 0.0,
                  fwhm: float = 1.2, shape: str = "gl", label: str = "", doublet: bool | None = None,
                  split: float | None = None, ratio: float | None = None, center_window: float = 1.0,
                  in_total: bool = True) -> dict:
    key = resolve_key(p, key)
    m = p.get_model(key) or RegionModel(region=p.spectra[key].region)
    name = m.unique_name(name or label or "p")
    orb = presets.orbital(m.region) or {}
    c = Component(name=name, label=label or name, shape=shape, in_total=in_total,
                  params=dict(center=Param(center, center - center_window, center + center_window),
                              fwhm=Param(fwhm, 0.2, 5.0)))
    if doublet is None:
        doublet = bool(orb.get("split"))
    if doublet:
        c.set_doublet(True, split or orb.get("split", 1.0), ratio or orb.get("ratio", 0.5))
        c.sub_labels = tuple(orb.get("sub") or ("", ""))
    m.components.append(c)
    s = p.spectra[key]
    if not m.fit_range:
        presets._clip_range(m, s, p.shift(s.sample))
    keep = {cc.name: cc.params["area"].value for cc in m.components if cc.name != name}
    presets.scale_areas(m, s, p.shift(s.sample))       # initial area for the new component only
    for cc in m.components:
        if cc.name in keep:
            cc.params["area"].value = keep[cc.name]
    p.set_model(key, m)
    return dict(key=key, added=name, components=m.names())


def remove_component(p: Project, key: str, name: str) -> dict:
    key = resolve_key(p, key)
    m = p.get_model(key)
    if m is None:
        raise ValueError("no model")
    m.components = [c for c in m.components if c.name != name]
    for _k, c, pn, prm in m.param_items():
        if prm.expr and f"{name}." in prm.expr:
            prm.expr = None
    p.set_model(key, m)
    return dict(key=key, components=m.names())


def set_param(p: Project, key: str, param: str, value: float | None = None, min: float | None = None,
              max: float | None = None, vary: bool | None = None, expr: str | None = None) -> dict:
    """param = 'Comp.param' e.g. 'Ir4.fwhm'. expr='' clears a link."""
    key = resolve_key(p, key)
    m = p.get_model(key)
    if m is None:
        raise ValueError("no model; apply a preset or add a component first")
    cn, pn = param.split(".", 1)
    c = m.comp(cn)
    if pn not in c.params:
        if pn == "shape" and value is not None:
            raise ValueError("use set_shape")
        raise KeyError(f"{cn} has no parameter {pn}: {list(c.params)}")
    prm = c.params[pn]
    if value is not None:
        prm.value = float(value)
    if min is not None:
        prm.min = float(min)
    if max is not None:
        prm.max = float(max)
    if vary is not None:
        prm.vary = bool(vary)
    if expr is not None:
        prm.expr = expr or None
    errs = m.validate()
    if errs:
        raise ValueError("; ".join(errs))
    p.set_model(key, m)
    return dict(key=key, param=param, **prm.to_json())


def set_background(p: Project, key: str, kind: str | None = None, lo: float | None = None,
                   hi: float | None = None, fit_lo: float | None = None, fit_hi: float | None = None) -> dict:
    key = resolve_key(p, key)
    m = p.get_model(key) or p.new_model(key)
    if kind:
        m.background.kind = kind
    if lo is not None:
        m.background.lo = lo
    if hi is not None:
        m.background.hi = hi
    if fit_lo is not None or fit_hi is not None:
        a, b = m.fit_range or (None, None)
        m.fit_range = (fit_lo if fit_lo is not None else a, fit_hi if fit_hi is not None else b)
    p.set_model(key, m)
    return dict(key=key, background=m.background.to_json(), fit_range=m.fit_range)


def fit(p: Project, keys=None, region=None, sample=None, n_starts: int = 3, diagnose_deep=False) -> list[dict]:
    out = []
    for k in keys_for(p, keys, region, sample):
        m, r = p.fit(k, n_starts=n_starts)
        d = dict(key=k, ok=r.ok, rms_pct=round(r.rms_pct, 3), fractions={a: round(b, 2) for a, b in r.fractions.items()},
                 components=_jsonable(r.summary_rows(m)), bound_hits=r.bound_hits)
        if diagnose_deep:
            d["diagnostics"] = _jsonable(diagnose(m, p.prepared(k, m), r, deep=True))
        out.append(d)
    return out


def diagnostics(p: Project, key: str, deep: bool = True) -> dict:
    key = resolve_key(p, key)
    m = p.get_model(key)
    if m is None:
        raise ValueError("no model")
    r = p.result(key)
    if r is None or not r.free_names:
        m, r = p.fit(key, m)
    return _jsonable(dict(key=key, **diagnose(m, p.prepared(key, m), r, deep=deep)))


def batch(p: Project, source: str, region: str | None = None, targets=None, fix=("fwhm",), n_starts=3) -> list[dict]:
    source = resolve_key(p, source)
    region = region or p.spectra[source].region
    tk = keys_for(p, targets, region)
    return _jsonable(p.batch_apply(source, tk, tuple(fix), n_starts))


def status(p: Project) -> dict:
    return _jsonable(p.summary())
