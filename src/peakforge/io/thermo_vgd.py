"""Thermo Scientific Avantage .VGD reader (K-Alpha etc.), standard library only.

A .VGD file is an OLE2 compound document (one spectrum per file). Layout determined from K-Alpha
files written by Avantage 5.9x and 6.10 (instrument K-Alpha_KAN_G2):
  stream 'VGData'       float64 intensities, one per energy point (summed over all scans)
  stream 'VGSpaceAxes'  u16 0, u16 2, u32 n_axes; per axis: 3 strings (u32 byte length + UTF-16:
                        name e.g. 'Kinetic Energy' — empty in 6.10 files —, symbol, unit), u32 npts,
                        f64 start, f64 step, 2 flag bytes
  stream 'VGDataAxes'   data dimensions (only 1-D spectra are supported)
  property set '\\x05Q5nw4m3lIjudbfwyAayojlptCa' (named properties): SourceEnergy, PassEnergy,
                        DwellTime (s), Scans, Mono, Instrument, Parent Experiment Object Name, ...
  '\\x05SummaryInformation' title (PID 2) = region name as typed in Avantage ('C1s Scan', 'Ir 4f 3')
Intensity: Avantage shows counts/s = VGData / (DwellTime · Scans) (checked against the axis maximum
stored in the companion .xml chart file), so VGData are counts and acq_time = DwellTime · Scans.
Energy axis is kinetic energy; BE = SourceEnergy − KE (Avantage convention, KE referenced to the
spectrometer Fermi level). An Avantage experiment is '<name>.vgp' + folder '<name>.DATA' with one .VGD
per region; reading the .vgp reads every .VGD in that folder (one sample).
"""
from __future__ import annotations

import os
import re
import struct

import numpy as np

from ..spectrum import Spectrum, normalize_region

OLE_MAGIC = bytes.fromhex("d0cf11e0a1b11ae1")
_END = 0xFFFFFFFA          # sector numbers >= this end a chain


class VGDError(ValueError):
    pass


# --------------------------------------------------------------------------- OLE2 compound file
def read_ole(path: str) -> dict[str, bytes]:
    """All streams of an OLE2 compound file, by entry name (directory hierarchy flattened)."""
    with open(path, "rb") as f:
        d = f.read()
    if d[:8] != OLE_MAGIC or len(d) < 512:
        raise VGDError("not an OLE2 compound file")
    ssz = 1 << struct.unpack_from("<H", d, 30)[0]
    mssz = 1 << struct.unpack_from("<H", d, 32)[0]
    n_fat, dir_start = struct.unpack_from("<II", d, 44)
    cutoff, mfat_start, _n_mfat, difat_start, n_difat = struct.unpack_from("<IIIII", d, 56)
    hdr = max(512, ssz)

    def sec(i: int) -> bytes:
        off = hdr + i * ssz
        if off >= len(d):     # a short last sector is tolerated (struct errors on it -> VGDError in read_vgd)
            raise VGDError("sector outside the file (truncated or corrupt file)")
        return d[off:off + ssz]

    difat = list(struct.unpack_from("<109I", d, 76))
    s, guard = difat_start, 0
    while s < _END and n_difat and guard < 10_000:
        vals = struct.unpack(f"<{ssz // 4}I", sec(s))
        difat += list(vals[:-1])
        s, n_difat, guard = vals[-1], n_difat - 1, guard + 1
    fat: list[int] = []
    for i in difat[:n_fat]:
        fat += struct.unpack(f"<{ssz // 4}I", sec(i))

    def chain(start: int, table: list[int], get) -> bytes:  # noqa: ANN001
        out, i, n = [], start, 0
        while i < _END:
            if i >= len(table) or n > len(table):
                raise VGDError("corrupt sector chain")
            out.append(get(i))
            i, n = table[i], n + 1
        return b"".join(out)

    dirs = chain(dir_start, fat, sec)
    entries = []
    for k in range(len(dirs) // 128):
        e = dirs[k * 128:(k + 1) * 128]
        nl = struct.unpack_from("<H", e, 64)[0]
        name = e[:max(min(nl, 64) - 2, 0)].decode("utf-16-le", errors="replace")
        start, size = struct.unpack_from("<IQ", e, 116)
        entries.append((name, e[66], start, size & 0xFFFFFFFF))
    if not entries:
        raise VGDError("empty compound file")
    ministream = chain(entries[0][2], fat, sec) if entries[0][2] < _END else b""
    minifat: list[int] = []
    if mfat_start < _END:
        mf = chain(mfat_start, fat, sec)
        minifat = list(struct.unpack(f"<{len(mf) // 4}I", mf))
    streams = {}
    for name, typ, start, size in entries[1:]:
        if typ != 2:                # 2 = stream
            continue
        if size < cutoff:
            data = chain(start, minifat, lambda i: ministream[i * mssz:(i + 1) * mssz])
        else:
            data = chain(start, fat, sec)
        streams[name] = data[:size]
    return streams


def _property_set(b: bytes) -> dict:
    """OLE property set -> {name or id: value}; names from the dictionary property (id 0)."""
    out: dict = {}
    if len(b) < 48 or b[:2] != b"\xfe\xff":
        return out
    nsec = struct.unpack_from("<I", b, 24)[0]
    for s in range(nsec):
        off = struct.unpack_from("<I", b, 28 + s * 20 + 16)[0]
        _size, n = struct.unpack_from("<II", b, off)
        ids = [struct.unpack_from("<II", b, off + 8 + 8 * i) for i in range(n)]
        # code page (PID 1, VT_I2): 1200 = UTF-16 names and strings; otherwise 8-bit text in that code page
        codepage = 1200
        for pid, po in ids:
            if pid == 1 and struct.unpack_from("<H", b, off + po)[0] == 2:
                codepage = struct.unpack_from("<H", b, off + po + 4)[0]

        def dec8(raw: bytes) -> str:
            try:
                return raw.decode("utf-8" if codepage == 65001 else f"cp{codepage}", errors="replace").rstrip("\0")
            except LookupError:
                return raw.decode("latin-1").rstrip("\0")
        names: dict[int, str] = {}
        for pid, po in ids:
            if pid != 0:
                continue
            p = off + po
            cnt = struct.unpack_from("<I", b, p)[0]
            p += 4
            for _ in range(cnt):
                i2, ln = struct.unpack_from("<II", b, p)
                p += 8
                if codepage == 1200:       # Unicode dictionary: ln characters, each entry padded to 4 bytes
                    names[i2] = b[p:p + ln * 2].decode("utf-16-le", errors="replace").rstrip("\0")
                    p += ln * 2
                    p += (-p) % 4
                else:                      # 8-bit dictionary: ln bytes, no padding between entries
                    names[i2] = dec8(b[p:p + ln])
                    p += ln
        for pid, po in ids:
            if pid in (0, 1) or pid >= 0x80000000:
                continue
            p = off + po
            vt = struct.unpack_from("<H", b, p)[0]
            p += 4
            v: object
            if vt == 5:
                v = struct.unpack_from("<d", b, p)[0]
            elif vt == 4:
                v = struct.unpack_from("<f", b, p)[0]
            elif vt in (3, 0x16):
                v = struct.unpack_from("<i", b, p)[0]
            elif vt in (0x13, 0x17):
                v = struct.unpack_from("<I", b, p)[0]
            elif vt == 2:
                v = struct.unpack_from("<h", b, p)[0]
            elif vt == 0xB:
                v = struct.unpack_from("<h", b, p)[0] != 0
            elif vt == 0x1F:
                ln = struct.unpack_from("<I", b, p)[0]
                v = b[p + 4:p + 4 + 2 * ln].decode("utf-16-le", errors="replace").rstrip("\0")
            elif vt in (0x1E, 8):
                ln = struct.unpack_from("<I", b, p)[0]
                raw = b[p + 4:p + 4 + ln]          # ln = bytes; under code page 1200 the bytes are UTF-16
                v = raw.decode("utf-16-le", errors="replace").rstrip("\0") if codepage == 1200 else dec8(raw)
            else:
                continue
            out[names.get(pid, pid)] = v
    return out


# --------------------------------------------------------------------------- VGD
def _axes(b: bytes) -> list[dict]:
    if len(b) < 8:
        raise VGDError("no energy axis")
    n_ax = struct.unpack_from("<I", b, 4)[0]
    p, out = 8, []
    for _ in range(n_ax):
        strs = []
        for _k in range(3):
            ln = struct.unpack_from("<I", b, p)[0]
            strs.append(b[p + 4:p + 4 + ln].decode("utf-16-le", errors="replace").rstrip("\0"))
            p += 4 + ln
        npts = struct.unpack_from("<I", b, p)[0]
        start, step = struct.unpack_from("<dd", b, p + 4)
        p += 4 + 16 + 2
        out.append(dict(name=strs[0], symbol=strs[1], unit=strs[2], npts=npts, start=start, step=step))
    return out


def _region_label(title: str, filename: str, span: float) -> str:
    stem = os.path.basename(filename)
    stem = stem[:-4] if stem.lower().endswith(".vgd") else stem
    s = (title or stem).strip()
    if not re.sub(r"[_\d\s]", "", s):                    # unnamed ('.VGD', '_0.VGD')
        return "Survey" if span > 300 else "Unknown"
    s = re.sub(r"_\d+$", "", s)                         # 'C1s Scan_0' (repeat) -> 'C1s Scan'
    s = re.sub(r"\s+scan$", "", s, flags=re.I)          # 'C1s Scan' -> 'C1s'
    if re.search(r"survey", s, re.I):
        return "Survey"
    return normalize_region(s)


def read_vgd(path: str) -> Spectrum:
    try:
        return _read_vgd(path)
    except struct.error as e:          # a structure runs past the end of a stream or a short sector
        raise VGDError(f"corrupt or truncated file ({e})") from e


def _read_vgd(path: str) -> Spectrum:
    st = read_ole(path)
    if "VGData" not in st or "VGSpaceAxes" not in st:
        raise VGDError("not an Avantage spectrum (.VGD without VGData)")
    props: dict = {}
    for k, v in st.items():
        if k.startswith("\x05") and "SummaryInformation" not in k:
            props.update(_property_set(v))
    summary = _property_set(st.get("\x05SummaryInformation", b""))
    ax = _axes(st["VGSpaceAxes"])
    if len(ax) != 1:
        raise VGDError(f"{len(ax)}-dimensional data (maps, profiles) are not supported")
    a = ax[0]
    y = np.frombuffer(st["VGData"], "<f8").astype(float)
    if len(y) != a["npts"]:
        raise VGDError(f"VGData has {len(y)} points, the axis {a['npts']}")
    hv = float(props.get("SourceEnergy") or 1486.68)
    e = a["start"] + a["step"] * np.arange(a["npts"])
    be = e if "binding" in a["name"].lower() else hv - e
    dwell = float(props.get("DwellTime") or 0.0)
    scans = int(props.get("Scans") or 1)
    if dwell <= 0:
        raise VGDError("no DwellTime in the file: counts/s unknown")
    t = dwell * scans
    meta = dict(format="thermo_vgd", reader="thermo_vgd", hv=hv, pass_energy=props.get("PassEnergy"),
                dwell=dwell, sweeps=scans, acq_time=t, instrument=props.get("Instrument", ""),
                mono=props.get("Mono"), experiment=props.get("Parent Experiment Object Name", ""),
                label=summary.get(2, ""))
    region = _region_label(str(summary.get(2, "")), path, float(np.ptp(be)))
    return Spectrum(region, be, y / t, sample=meta["experiment"] or os.path.basename(os.path.dirname(path)),
                    source_file=path, meta=meta)


def data_folder(vgp: str) -> str:
    """'<dir>/<name>.vgp' -> '<dir>/<name>.DATA' (case-insensitive match)."""
    d, name = os.path.split(os.path.abspath(vgp))
    stem = os.path.splitext(name)[0]
    for e in os.listdir(d or "."):
        if e.lower() == (stem + ".data").lower() and os.path.isdir(os.path.join(d, e)):
            return os.path.join(d, e)
    raise VGDError(f"no folder {stem}.DATA next to {name} (copy the .vgp together with its .DATA folder)")


def read_experiment(path: str) -> list[Spectrum]:
    """.vgp -> all spectra in '<name>.DATA'; .VGD -> that spectrum. Repeated regions get index 1, 2, …"""
    if path.lower().endswith(".vgp"):
        folder = data_folder(path)
        files = sorted(f for f in os.listdir(folder) if f.lower().endswith(".vgd"))
        out = []
        for f in files:
            try:
                out.append(read_vgd(os.path.join(folder, f)))
            except VGDError as e:
                raise VGDError(f"{f}: {e}") from e
    else:
        out = [read_vgd(path)]
    # Avantage keeps an edited copy of a spectrum as '<name>_0.VGD' etc. (on these data: the same scan with
    # the energy axis moved by the user's charge shift; intensities equal or re-sampled within a few %).
    # Kept as separate spectra; the offset is recorded so the user can tell (meta 'avantage_shift').
    by_file = {os.path.splitext(os.path.basename(s.source_file))[0].lower(): s for s in out}
    for stem, s in by_file.items():
        m = re.match(r"(.*)_\d+$", stem)
        base = by_file.get(m.group(1)) if m else None
        if base is not None and len(base.be) == len(s.be):
            s.meta["avantage_copy_of"] = os.path.basename(base.source_file)
            s.meta["avantage_shift"] = round(float(s.be[0] - base.be[0]), 4)
    seen: dict[str, int] = {}
    for s in out:
        s.index = seen.get(s.region, 0)
        seen[s.region] = s.index + 1
    return out
