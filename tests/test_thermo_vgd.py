"""Thermo Avantage .VGD reader: parsers on synthetic bytes (always), real files when PEAKFORGE_CAL_DATA
points to a folder with Avantage experiments (.vgp + .DATA; local only, never committed)."""
import glob
import os
import struct
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from peakforge.core import quant  # noqa: E402
from peakforge.io import registry, thermo_vgd as tv  # noqa: E402


def _s(text: str) -> bytes:
    b = (text + "\0").encode("utf-16-le") if text else "\0".encode("utf-16-le")
    return struct.pack("<I", len(b)) + b


def _axes(name="", n=191, start=1188.68, step=0.1):
    return (struct.pack("<HHI", 0, 2, 1) + _s(name) + _s("") + _s("") + struct.pack("<I", n)
            + struct.pack("<dd", start, step) + b"\x01\x01")


def test_axes_new_and_old_layout():
    a = tv._axes(_axes())
    assert a[0]["npts"] == 191 and a[0]["start"] == pytest.approx(1188.68) and a[0]["step"] == pytest.approx(0.1)
    b = tv._axes(_axes("Kinetic Energy", 201, 1188.6, 0.1))
    assert b[0]["name"] == "Kinetic Energy" and b[0]["npts"] == 201


def _propset(props: dict) -> bytes:
    """Minimal OLE property set: one section, dictionary (id 0) + float/int/string properties."""
    entries, dic = [], []
    for i, (k, v) in enumerate(props.items(), start=2):
        name = (k + "\0").encode("utf-16-le")
        d = struct.pack("<II", i, len(k) + 1) + name
        dic.append(d + b"\0" * ((-len(d)) % 4))
        if isinstance(v, float):
            val = struct.pack("<HHf", 4, 0, v)
        elif isinstance(v, int):
            val = struct.pack("<HHi", 3, 0, v)
        else:
            s = (v + "\0").encode("utf-16-le")
            val = struct.pack("<HHI", 0x1F, 0, len(v) + 1) + s + b"\0" * ((-len(s)) % 4)
        entries.append((i, val))
    dict_val = struct.pack("<I", len(dic)) + b"".join(dic)
    vals = [(0, dict_val)] + entries
    n = len(vals)
    off = 8 + 8 * n
    table, blob = b"", b""
    for pid, v in vals:
        table += struct.pack("<II", pid, off + len(blob))
        blob += v
    section = struct.pack("<II", 8 + 8 * n + len(blob), n) + table + blob
    head = b"\xfe\xff\x00\x00" + b"\0" * 20 + struct.pack("<I", 1) + b"\0" * 16 + struct.pack("<I", 48)
    return head + section


def test_property_set_roundtrip():
    p = tv._property_set(_propset(dict(DwellTime=0.05, Scans=5, PassEnergy=50.0, Instrument="K-Alpha")))
    assert p["DwellTime"] == pytest.approx(0.05) and p["Scans"] == 5 and p["Instrument"] == "K-Alpha"


@pytest.mark.parametrize("title,fname,span,exp", [
    ("C1s Scan", "C1s Scan.VGD", 19, "C 1s"), ("", "C1s Scan_0.VGD", 19, "C 1s"),
    ("Ir 4f 3", "Ir 4f 3.VGD", 10, "Ir 4f"), ("Co 2p3 3", "x.VGD", 40, "Co 2p3/2"),
    ("XPS Survey", "XPS Survey.VGD", 1360, "Survey"), ("Su1s 1", "Su1s 1.VGD", 1100, "Survey"),
    ("", ".VGD", 1100, "Survey"), ("", "_0.VGD", 1100, "Survey"),
])
def test_region_labels(title, fname, span, exp):
    assert tv._region_label(title, fname, span) == exp


def test_detect_by_suffix_only(tmp_path):
    """.xls is an OLE2 file too: only .vgp/.VGD go to the Thermo reader."""
    for name in ("a.VGD", "b.vgp", "c.xls"):
        (tmp_path / name).write_bytes(tv.OLE_MAGIC + b"\0" * 600)
    assert registry.detect_format(str(tmp_path / "a.VGD"))[0] == "thermo_vgd"
    assert registry.detect_format(str(tmp_path / "b.vgp"))[0] == "thermo_vgd"
    assert registry.detect_format(str(tmp_path / "c.xls"))[0] == "table"


def test_not_ole_is_a_read_error(tmp_path):
    f = tmp_path / "x.VGD"
    f.write_bytes(b"hello" * 200)
    with pytest.raises(registry.ReadError):
        registry.read_file(str(f))


# --------------------------------------------------------------------------- real data (local only)
DATA = os.environ.get("PEAKFORGE_CAL_DATA")
real = pytest.mark.skipif(not DATA, reason="set PEAKFORGE_CAL_DATA to a folder with Avantage .vgp/.DATA")


@real
def test_real_experiments_read():
    vgps = glob.glob(os.path.join(DATA, "**", "*.vgp"), recursive=True)
    n = 0
    for f in vgps:
        try:
            sps = registry.read_file(f)
        except registry.ReadError as e:
            assert "no spectra" in str(e), e          # empty grids/workspaces only
            continue
        for s in sps:
            n += 1
            assert np.all(np.diff(s.be) > 0) and np.all(np.isfinite(s.cps)) and s.acq_time() > 0
            assert s.region != "Unknown" and not s.region.endswith(".VGD")
            if s.region == "C 1s":                    # BE axis sane: C 1s window in 270–310 eV
                assert 270 < s.be.min() < s.be.max() < 310
    assert n > 20


@real
def test_auto_charge_matches_avantage_shifts():
    """Benchmark: the user's own charge shifts in Avantage (stored as '<name>_0.VGD' copies moved on the
    energy axis) vs PeakForge's automatic C 1s reference on the original file. Avantage shifts are set by
    hand and rounded to 0.05–0.1 eV; tolerance 0.4 eV each, median |difference| ≤ 0.1 eV."""
    diffs = []
    for f in glob.glob(os.path.join(DATA, "**", "*_0.VGD"), recursive=True):
        base = f[:-6] + ".VGD"
        if not os.path.exists(base):
            continue
        a, b = tv.read_vgd(base), tv.read_vgd(f)
        if a.region != "C 1s" or len(a.be) != len(b.be):
            continue
        manual = float(b.be[0] - a.be[0])
        r = quant.find_reference(a.be, a.cps, 284.8)
        assert r.confidence == "high", (f, r.reasons)
        diffs.append(284.8 - r.position - manual)
    assert len(diffs) >= 5
    assert max(abs(d) for d in diffs) <= 0.4, diffs
    assert float(np.median(np.abs(diffs))) <= 0.1, diffs
