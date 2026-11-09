"""PHI MultiPak / SmartSoft .spe reader (ASCII header + little-endian binary block).

Layout determined from PHI GENESIS / VersaProbe files:
  header lines ... 'EOFH'
  binary: int32 group, int32 n_traces, int32 header_len, int32 ?
          n_traces x 96-byte trace records:
             [0] trace no, [3] region no, [5] n points, [19] byte length, [20] byte offset
          float32 data (counts per second) at the stated offsets (relative to binary start)
Energy axis from 'SpectralRegDef: idx idx label Z npts step start end start2 end2 dwell PE AREA'.
"""
from __future__ import annotations

import os
import struct

import numpy as np

from ..spectrum import Spectrum, normalize_region


def _parse_header(text: str) -> dict:
    h: dict = {"regions": {}, "regions2": {}}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        if key == "SpectralRegDef":
            p = val.split()
            h["regions"][int(p[0])] = dict(label=p[2], z=int(p[3]), npts=int(p[4]),
                                          step=float(p[5]), start=float(p[6]), end=float(p[7]),
                                          dwell=float(p[10]), pass_energy=float(p[11]))
        elif key == "SpectralRegDef2":
            p = val.split()
            h["regions2"][int(p[0])] = dict(sweeps=int(float(p[2])))
        else:
            h.setdefault(key, val)
    return h


def read_spe(path: str) -> list[Spectrum]:
    raw = open(path, "rb").read()
    i = raw.find(b"EOFH")
    if not raw.startswith(b"SOFH") or i < 0:
        raise ValueError(f"{path}: not a PHI .spe file")
    start = raw.find(b"\n", i) + 1
    hdr = _parse_header(raw[:i].decode("latin-1"))
    data = raw[start:]
    group, n_traces, _hlen, _x = struct.unpack("<4i", data[:16])
    src = hdr.get("XraySource", "")
    try:
        hv = float(src.split()[1])
    except (IndexError, ValueError):
        hv = 1486.6
    base = os.path.splitext(os.path.basename(path))[0]
    out: list[Spectrum] = []
    seen: dict[str, int] = {}
    for t in range(n_traces):
        rec = struct.unpack("<24i", data[16 + 96 * t: 16 + 96 * (t + 1)])
        reg_no, npts, nbytes, off = rec[3], rec[5], rec[19], rec[20]
        reg = hdr["regions"].get(reg_no)
        if reg is None:
            continue
        y = np.frombuffer(data[off: off + nbytes], dtype="<f4").astype(float)
        if len(y) != npts:
            y = y[:npts]
        be = reg["start"] + reg["step"] * np.arange(len(y))
        region = normalize_region(reg["label"])
        seen[region] = seen.get(region, -1) + 1
        sweeps = hdr["regions2"].get(reg_no, {}).get("sweeps", 1)
        meta = dict(format="PHI SPE", technique=hdr.get("Technique", "XPS"), source=src,
                    photon_energy=hv, pass_energy=reg["pass_energy"], dwell=reg["dwell"],
                    sweeps=sweeps, work_function=hdr.get("AnalyserWorkFcn", ""),
                    date=hdr.get("FileDate", ""), instrument=hdr.get("InstrumentModel", ""),
                    institution=hdr.get("Institution", ""))
        out.append(Spectrum(region=region, be=be, cps=y, sample=base, source_file=path,
                            index=seen[region], meta=meta))
    return out
