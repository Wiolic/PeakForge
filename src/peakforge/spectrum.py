"""Core spectrum container shared by readers, fitting, GUI and exports."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import numpy as np

_ORBITAL_RE = re.compile(r"^\s*([A-Z][a-z]?)\s*(\d)\s*([spdf])(\s*\d\s*/\s*2|\d)?\s*$")
# short j notation used by instruments: Fe2p3 = Fe 2p3/2, Ce3d5 = Ce 3d5/2, Pt4f7 = Pt 4f7/2
_J_SHORT = {"p": {"1": "1/2", "3": "3/2"}, "d": {"3": "3/2", "5": "5/2"}, "f": {"5": "5/2", "7": "7/2"}}


def normalize_region(label: str) -> str:
    """'Ir4f' / 'Ir 4f' / 'Ir 4f 4' / 'Fe2p3' / 'Su1s' -> 'Ir 4f' / 'Ir 4f' / 'Ir 4f' / 'Fe 2p3/2' / 'Survey'."""
    s = label.strip()
    if s.lower().startswith("su") and "1s" in s.lower():
        return "Survey"
    s = re.sub(r"\s+\d+$", "", s) if not _ORBITAL_RE.match(s) else s   # VAMAS ids end with a counter: "C 1s 1"
    m = _ORBITAL_RE.match(s)
    if m:
        el, n, l, j = m.groups()
        out = f"{el} {n}{l}"
        if j:
            j = j.replace(" ", "")
            j = _J_SHORT.get(l, {}).get(j, j) if "/" not in j else j
            if "/" in j:
                out += j
        return out
    return s


def element_of(region: str) -> str | None:
    m = re.match(r"([A-Z][a-z]?)(\s*\d[spdf]|$)", region.strip())
    return m.group(1) if m else None


@dataclass
class Spectrum:
    """One XPS region. Binding energy ascending; intensity in counts per second."""

    region: str
    be: np.ndarray
    cps: np.ndarray
    sample: str = ""
    source_file: str = ""
    index: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        be = np.asarray(self.be, float)
        y = np.asarray(self.cps, float)
        o = np.argsort(be)
        self.be, self.cps = be[o], y[o]

    @property
    def element(self) -> str | None:
        return element_of(self.region)

    @property
    def is_survey(self) -> bool:
        return self.region == "Survey" or (self.be.max() - self.be.min()) > 300

    @property
    def key(self) -> str:
        return f"{self.sample}/{self.region}" + (f"#{self.index}" if self.index else "")

    def counts(self) -> np.ndarray:
        """Estimated total counts (for Poisson weighting)."""
        dwell = float(self.meta.get("dwell", 1.0) or 1.0)
        sweeps = float(self.meta.get("sweeps", 1) or 1)
        return np.clip(self.cps * dwell * sweeps, 1.0, None)

    def to_dict(self) -> dict:
        return dict(region=self.region, sample=self.sample, source_file=self.source_file,
                    index=self.index, npts=len(self.be), be_min=float(self.be.min()),
                    be_max=float(self.be.max()), meta=self.meta)
