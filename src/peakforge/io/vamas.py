"""VAMAS (ISO 14976) reader.

Follows the field order of ISO 14976:1998. Handles NORM / SDP / MAP experiment modes,
REGULAR and IRREGULAR scans, any number of corresponding variables. The first corresponding
variable is taken as the intensity; for XPS with a kinetic-energy abscissa it is converted to
binding energy using the source characteristic energy.
"""
from __future__ import annotations

import os

import numpy as np

from ..spectrum import Spectrum, normalize_region

_SPUTTER_MODES = {"MAPDP", "MAPSVDP", "SDP", "SDPSV"}
_SPUTTER_TECH = {"FABMS", "FABMS energy spec", "ISS", "SIMS", "SIMS energy spec", "SNMS",
                 "SNMS energy spec"}
_MAP_MODES = {"MAP", "MAPDP"}
_FOV_MODES = {"MAP", "MAPDP", "MAPSV", "MAPSVDP", "SEM"}
_LINESCAN_MODES = {"MAPSV", "MAPSVDP", "SEM"}


class _Lines:
    def __init__(self, text: str):
        self.l = text.splitlines()
        self.i = 0

    def s(self) -> str:
        v = self.l[self.i].rstrip("\r")
        self.i += 1
        return v

    def n(self) -> float:
        return float(self.s().strip())

    def k(self) -> int:
        return int(float(self.s().strip()))

    def skip(self, n: int):
        self.i += n


def read_vamas(path: str, keep_comments: bool = False) -> list[Spectrum]:
    """keep_comments: store each block's comment lines in meta["comment"] (e.g. CasaXPS
    "CASA region/comp" model lines); off by default so project files stay small."""
    with open(path, "r", encoding="latin-1") as f:
        L = _Lines(f.read())
    if not L.s().startswith("VAMAS"):
        raise ValueError(f"{path}: not a VAMAS file")
    institution, instrument, operator, experiment = L.s(), L.s(), L.s(), L.s()  # noqa: F841 (header fields read to advance the stream)
    L.skip(L.k())                       # header comment lines
    exp_mode = L.s().strip()
    scan_mode = L.s().strip()
    if exp_mode in {"MAP", "MAPDP", "NORM", "SDP"}:
        L.k()                           # number of spectral regions
    if exp_mode in _MAP_MODES:
        L.skip(3)
    n_expvar = L.k()
    L.skip(2 * n_expvar)
    n_incl = L.k()
    L.skip(abs(n_incl))
    L.k()                               # manually entered items
    n_fut_exp = L.k()
    n_fut_blk = L.k()
    L.skip(n_fut_exp)
    n_blocks = L.k()

    base = os.path.splitext(os.path.basename(path))[0]
    out: list[Spectrum] = []
    seen: dict[str, int] = {}
    for _ in range(n_blocks):
        block_id = L.s().strip()
        sample_id = L.s().strip()
        date = [L.k() for _ in range(6)]
        L.k()                           # GMT offset
        comment = [L.s() for _ in range(L.k())]     # block comment
        tech = L.s().strip()
        if exp_mode in _MAP_MODES:
            L.skip(2)
        L.skip(n_expvar)
        source = L.s().strip()
        if exp_mode in _SPUTTER_MODES or tech in _SPUTTER_TECH:
            L.skip(3)
        hv = L.n()
        source_strength = L.n()
        L.skip(2)                       # beam width x, y
        if exp_mode in _FOV_MODES:
            L.skip(2)
        if exp_mode in _LINESCAN_MODES:
            L.skip(6)
        L.skip(2)                       # source polar / azimuth
        analyser_mode = L.s().strip()
        pass_energy = L.n()
        if tech == "AES diff":
            L.skip(1)
        L.skip(1)                       # magnification
        work_fn = L.n()
        L.skip(1)                       # target bias
        L.skip(2)                       # analysis width x,y
        L.skip(2)                       # take-off polar/azimuth
        species = L.s().strip()
        transition = L.s().strip()
        L.skip(1)                       # charge of detected particle
        if scan_mode == "REGULAR":
            x_label = L.s().strip()
            L.s()                       # units
            x0 = L.n()
            dx = L.n()
        else:
            x_label, x0, dx = "", 0.0, 0.0
        n_corr = L.k()
        corr_labels, corr_units = [], []
        for _c in range(n_corr):
            corr_labels.append(L.s().strip())
            corr_units.append(L.s().strip())
        L.s()                           # signal mode
        dwell = L.n()
        scans = L.k()
        L.skip(1)                       # signal time correction
        if exp_mode in _SPUTTER_MODES:
            L.skip(7)
        L.skip(3)                       # sample normal tilt, azimuth, rotation
        n_add = L.k()
        add = {}
        for _a in range(n_add):
            lab = L.s().strip(); L.s(); add[lab] = L.s().strip()
        L.skip(n_fut_blk)
        n_ord = L.k()
        L.skip(2 * n_corr)              # min / max per corresponding variable
        vals = np.array([float(L.s()) for _o in range(n_ord)])
        vals = vals.reshape(-1, n_corr) if n_corr > 1 else vals.reshape(-1, 1)
        npts = vals.shape[0]
        if scan_mode == "REGULAR":
            x = x0 + dx * np.arange(npts)
            y = vals[:, 0]
        else:
            x, y = vals[:, 0], vals[:, 1]
        if x_label.lower().startswith("kinetic"):
            be = hv - x
        else:
            be = x
        region = normalize_region(f"{species} {transition}".strip() or block_id)
        if region in ("", " "):
            region = normalize_region(block_id)
        dwell_eff = dwell if dwell and dwell < 1e30 else 1.0
        # ISO 14976: ordinate = counts per channel summed over 'scans' sweeps of 'dwell' s each.
        # Files that already store count rates (unit c/s) are taken as is.
        per_second = corr_units[0].lower().replace(" ", "") in ("c/s", "cps", "counts/s", "s-1", "1/s")
        acq = dwell_eff * max(scans, 1)
        cps = y if per_second else y / acq
        seen[region] = seen.get(region, -1) + 1
        meta = dict(format="VAMAS", technique=tech, source=source, photon_energy=hv,
                    source_strength=source_strength, analyser_mode=analyser_mode,
                    pass_energy=pass_energy, work_function=work_fn, dwell=dwell_eff,
                    sweeps=max(scans, 1), acq_time=acq, y_unit=corr_units[0], date="%04d-%02d-%02d %02d:%02d:%02d" % tuple(date),
                    block_id=block_id, sample_id=sample_id, institution=institution,
                    instrument=instrument, extra=add)
        if n_corr > 1 and "transmission" in corr_labels[1].lower():
            meta["transmission"] = vals[:, 1].tolist()
        if keep_comments:
            meta["comment"] = "\n".join(comment)
        out.append(Spectrum(region=region, be=be, cps=cps, sample=base, source_file=path,
                            index=seen[region], meta=meta))
    return out
