"""Peak model: parameters with bounds / links, components (singlet or spin-orbit doublet),
background settings. Everything round-trips through plain JSON dicts.

Parameter references in expressions use '<component>.<param>', e.g.
    "Ir0.center + 1.1"      "Ir4.fwhm"      "O_lat.fwhm * 1.0"
Doublet parameters are 'split' and 'ratio' on the component: "Ir0.split".
"""
from __future__ import annotations

import ast
import functools
import math
import operator
import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from . import background as _bg
from . import lineshapes

_REF = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
_SAFE = {"abs": abs, "min": min, "max": max, "sqrt": math.sqrt, "exp": math.exp,
         "log": math.log, "pi": math.pi}


@dataclass
class Param:
    value: float
    min: float = -np.inf
    max: float = np.inf
    vary: bool = True
    expr: str | None = None

    @property
    def free(self) -> bool:
        return self.vary and not self.expr

    def to_json(self):
        d: dict[str, Any] = {"value": float(self.value)}
        if np.isfinite(self.min):
            d["min"] = float(self.min)
        if np.isfinite(self.max):
            d["max"] = float(self.max)
        if not self.vary:
            d["vary"] = False
        if self.expr:
            d["expr"] = self.expr
        return d

    @classmethod
    def from_json(cls, v) -> "Param":
        """number | [value, min, max] | [value] | {"value", "min", "max", "vary", "expr"} | "expr" """
        if isinstance(v, Param):
            return Param(v.value, v.min, v.max, v.vary, v.expr)
        if isinstance(v, (int, float)):
            return cls(float(v))
        if isinstance(v, str):
            return cls(0.0, expr=v)
        if isinstance(v, (list, tuple)):
            if len(v) == 1:
                return cls(float(v[0]), vary=False)
            return cls(float(v[0]), float(v[1]), float(v[2]))
        lo, hi = v.get("min"), v.get("max")          # null = unbounded (same as schema.py)
        return cls(float(v.get("value") or 0.0), -np.inf if lo is None else float(lo),
                   np.inf if hi is None else float(hi), bool(v.get("vary", True)), v.get("expr") or None)


@dataclass
class Component:
    name: str                     # identifier used in expressions (no spaces)
    label: str = ""               # display label, unicode allowed: 'Ir⁴⁺'
    shape: str = "gl"
    params: dict[str, Param] = field(default_factory=dict)   # center, fwhm, area, + shape extras
    doublet: bool = False         # second line at center+split with area*ratio
    sub_labels: tuple[str, str] = ("", "")   # e.g. ('4f7/2', '4f5/2')
    in_total: bool = True         # include in state fractions (False for satellites)
    group: str = ""               # optional state/group for summing
    color: str | None = None

    def __post_init__(self):
        if not self.label:
            self.label = self.name
        defaults = {"center": 0.0, "fwhm": 1.0, "area": 1.0}
        for k, v in defaults.items():
            self.params.setdefault(k, Param(v))
        for k, (v, lo, hi) in lineshapes.SHAPES[self.shape]["extra"].items():
            self.params.setdefault(k, Param(v, lo, hi))
        if self.doublet:
            self.params.setdefault("split", Param(1.0, vary=False))
            self.params.setdefault("ratio", Param(0.5, vary=False))
        self.params.setdefault("fwhm", Param(1.0))
        if np.isinf(self.params["area"].min):
            self.params["area"].min = 0.0
        if np.isinf(self.params["fwhm"].min):
            self.params["fwhm"].min = 0.05

    def set_shape(self, shape: str):
        old = self.shape
        self.shape = shape
        for k in lineshapes.SHAPES[old]["extra"]:
            if k not in lineshapes.SHAPES[shape]["extra"]:
                self.params.pop(k, None)
        for k, (v, lo, hi) in lineshapes.SHAPES[shape]["extra"].items():
            self.params.setdefault(k, Param(v, lo, hi))

    def set_doublet(self, on: bool, split: float = 1.0, ratio: float = 0.5):
        self.doublet = on
        if on:
            self.params.setdefault("split", Param(split, vary=False))
            self.params.setdefault("ratio", Param(ratio, vary=False))
        else:
            self.params.pop("split", None)
            self.params.pop("ratio", None)

    def shape_kw(self, vals: dict[str, float]) -> dict[str, float]:
        return {k: vals[k] for k in lineshapes.SHAPES[self.shape]["extra"]}

    def lines(self, x: np.ndarray, vals: dict[str, float]) -> list[np.ndarray]:
        """[main line] or [main, partner] (area-weighted profiles)."""
        kw = self.shape_kw(vals)
        a, c, w = vals["area"], vals["center"], vals["fwhm"]
        if not self.doublet:
            return [a * lineshapes.profile(self.shape, x, c, w, **kw)]
        r = vals["ratio"]
        return [a * lineshapes.profile(self.shape, x, c, w, **kw),
                a * r * lineshapes.profile(self.shape, x, c + vals["split"], w, **kw)]

    def total_area(self, vals: dict[str, float]) -> float:
        return vals["area"] * (1 + vals["ratio"]) if self.doublet else vals["area"]

    def to_json(self):
        d = dict(name=self.name, label=self.label, shape=self.shape,
                 params={k: p.to_json() for k, p in self.params.items()})
        if self.doublet:
            d["doublet"] = True
            d["sub_labels"] = list(self.sub_labels)
        if not self.in_total:
            d["in_total"] = False
        if self.group:
            d["group"] = self.group
        if self.color:
            d["color"] = self.color
        return d

    @classmethod
    def from_json(cls, d) -> "Component":
        c = cls(name=d["name"], label=d.get("label", ""), shape=d.get("shape", "gl"),
                params={k: Param.from_json(v) for k, v in d.get("params", {}).items()},
                doublet=bool(d.get("doublet", False)),
                sub_labels=tuple(d.get("sub_labels", ("", ""))),
                in_total=bool(d.get("in_total", True)), group=d.get("group", ""),
                color=d.get("color"))
        return c


@dataclass
class BackgroundSpec:
    kind: str = "shirley"
    lo: float | None = None       # BE limits; None = data range
    hi: float | None = None
    avg: float = 0.5              # eV averaged at each end point
    tougaard: tuple = _bg.TOUGAARD_U2        # (B, C, D), see core/background.py

    def to_json(self):
        return dict(kind=self.kind, lo=self.lo, hi=self.hi, avg=self.avg, tougaard=list(self.tougaard))

    @classmethod
    def from_json(cls, d) -> "BackgroundSpec":
        d = d or {}
        return cls(kind=d.get("kind", "shirley"), lo=d.get("lo"), hi=d.get("hi"),
                   avg=float(d.get("avg", 0.5)), tougaard=_bg.normalize_tougaard(d.get("tougaard")))


@dataclass
class RegionModel:
    region: str = ""
    components: list[Component] = field(default_factory=list)
    background: BackgroundSpec = field(default_factory=BackgroundSpec)
    fit_range: tuple[float, float] | None = None     # BE window used for fitting (after charge shift)
    weighting: str = "none"                          # 'none' | 'poisson'
    note: str = ""
    preset: str = ""
    legend_order: list[str] = field(default_factory=list)   # component names; colours keep list order

    # ---------------------------------------------------------------- access
    def legend_components(self) -> list["Component"]:
        """Components in legend order (legend_order first, then the rest in list order)."""
        names = [n for n in self.legend_order if n in self.names()]
        return [self.comp(n) for n in names] + [c for c in self.components if c.name not in names]

    def comp(self, name: str) -> Component:
        for c in self.components:
            if c.name == name:
                return c
        raise KeyError(name)

    def names(self) -> list[str]:
        return [c.name for c in self.components]

    def unique_name(self, base: str = "p") -> str:
        base = re.sub(r"[^A-Za-z0-9_]", "_", base) or "p"
        if base[0].isdigit():
            base = "p" + base
        if base not in self.names():
            return base
        i = 2
        while f"{base}{i}" in self.names():
            i += 1
        return f"{base}{i}"

    def param_items(self):
        for c in self.components:
            for k, p in c.params.items():
                yield f"{c.name}.{k}", c, k, p

    # ---------------------------------------------------------------- evaluation
    def resolve(self, overrides: dict[str, float] | None = None) -> dict[str, dict[str, float]]:
        """Return {component: {param: value}} with expressions evaluated (iteratively)."""
        vals = {c.name: {k: float(p.value) for k, p in c.params.items()} for c in self.components}
        if overrides:
            for key, v in overrides.items():
                cn, pn = key.split(".", 1)
                vals[cn][pn] = float(v)
        exprs = [(c.name, k, p.expr) for c in self.components for k, p in c.params.items() if p.expr]
        ns_vals = vals
        for _ in range(len(exprs) + 1):
            changed = False
            for cn, pn, ex in exprs:
                v = eval_expr(ex, ns_vals)
                if v != ns_vals[cn][pn]:
                    ns_vals[cn][pn] = v
                    changed = True
            if not changed:
                break
        return vals

    def validate(self) -> list[str]:
        errs = []
        names = set(self.names())
        for key, c, k, p in self.param_items():
            if p.expr:
                try:
                    _parse(p.expr)
                except ValueError as e:
                    errs.append(f"{key}: {e}")
                    continue
                for cn, pn in _REF.findall(p.expr):
                    if cn not in names:
                        errs.append(f"{key}: unknown component '{cn}' in '{p.expr}'")
                    elif pn not in self.comp(cn).params:
                        errs.append(f"{key}: '{cn}' has no parameter '{pn}'")
        return errs

    # ---------------------------------------------------------------- json
    def to_json(self):
        return dict(region=self.region, preset=self.preset, note=self.note, weighting=self.weighting,
                    fit_range=list(self.fit_range) if self.fit_range else None,
                    background=self.background.to_json(),
                    components=[c.to_json() for c in self.components],
                    **({"legend_order": list(self.legend_order)} if self.legend_order else {}))

    @classmethod
    def from_json(cls, d) -> "RegionModel":
        return cls(region=d.get("region", ""), preset=d.get("preset", ""), note=d.get("note", ""),
                   weighting=d.get("weighting", "none"), legend_order=list(d.get("legend_order", [])),
                   fit_range=tuple(d["fit_range"]) if d.get("fit_range") else None,
                   background=BackgroundSpec.from_json(d.get("background")),
                   components=[Component.from_json(c) for c in d.get("components", [])])

    def copy(self) -> "RegionModel":
        return RegionModel.from_json(self.to_json())


_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
           ast.Div: operator.truediv, ast.Pow: operator.pow}
_UNOPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_FUNCS = {k: v for k, v in _SAFE.items() if callable(v)}
_CONSTS = {k: v for k, v in _SAFE.items() if not callable(v)}


@functools.lru_cache(maxsize=4096)
def _parse(expr: str) -> ast.expr:
    """Parse and whitelist an expression: numbers, + - * / **, unary ±, the functions in _SAFE,
    the constant pi and '<component>.<param>' references. Anything else raises ValueError."""
    try:
        tree = ast.parse(expr.strip(), mode="eval").body
    except SyntaxError as e:
        raise ValueError(f"invalid expression '{expr}': {e.msg}") from None

    def check(n):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            return
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            check(n.left); check(n.right); return
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNOPS:
            check(n.operand); return
        if isinstance(n, ast.Name) and n.id in _CONSTS:
            return
        if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name) and not n.attr.startswith("_") \
                and not n.value.id.startswith("_"):
            return
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCS \
                and not n.keywords:
            for a in n.args:
                check(a)
            return
        raise ValueError(f"not allowed in expression '{expr}': {ast.dump(n)[:60]}")
    check(tree)
    return tree


def eval_expr(expr: str, vals: dict[str, dict[str, float]]) -> float:
    """Evaluate a parameter expression such as 'Ir0.center + 1.1' without Python eval()."""
    def ev(n):
        if isinstance(n, ast.Constant):
            return float(n.value)
        if isinstance(n, ast.BinOp):
            return _BINOPS[type(n.op)](ev(n.left), ev(n.right))
        if isinstance(n, ast.UnaryOp):
            return _UNOPS[type(n.op)](ev(n.operand))
        if isinstance(n, ast.Name):
            return float(_CONSTS[n.id])
        if isinstance(n, ast.Attribute):
            cn, pn = n.value.id, n.attr
            if cn in vals and pn in vals[cn]:
                return float(vals[cn][pn])
            raise KeyError(f"unknown reference {cn}.{pn}")
        if isinstance(n, ast.Call):
            return float(_FUNCS[n.func.id](*[ev(a) for a in n.args]))
        raise ValueError(expr)
    try:
        return float(ev(_parse(expr)))
    except (OverflowError, ZeroDivisionError) as e:
        raise ValueError(f"expression '{expr}': {e}") from None
