"""Phase 2: reader registry, column templates + wizard back end, validation (schema.py), logging and
the diagnostics bundle."""
import json
import os
import sys
import zipfile

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from peakforge import logs, ops, presets, schema  # noqa: E402
from peakforge.core import lineshapes  # noqa: E402
from peakforge.io import ReadError, detect_format, list_formats, read_file  # noqa: E402
from peakforge.io.wizard import add_template, build_template, inspect_table, try_read  # noqa: E402
from peakforge.project import Project  # noqa: E402
from peakforge.schema import SchemaError  # noqa: E402


def _peak(x, c=60.9, w=1.0, a=3000.0, bg=200.0):
    return bg + a * lineshapes.profile("gaussian", x, c, w)


# ------------------------------------------------------------------ registry
def test_detect_by_content_and_suffix(tmp_path):
    v = tmp_path / "noext"
    v.write_bytes(b"VAMAS Surface Chemical Analysis Standard Data Transfer Format 1988 May 4\n")
    s = tmp_path / "a.bin"
    s.write_bytes(b"SOFH\nEOFH\n")
    c = tmp_path / "a.csv"
    c.write_text("BE,I\n1,2\n", encoding="utf-8")
    t = tmp_path / "plain.asc"
    t.write_text("\n".join(f"{60 + i * 0.1:.1f} {100 + i}" for i in range(20)), encoding="utf-8")
    junk = tmp_path / "x.zzz"
    junk.write_bytes(bytes(range(256)))
    assert detect_format(str(v))[0] == "vamas"
    assert detect_format(str(s))[0] == "phi_spe"
    assert detect_format(str(c))[0] == "table"
    assert detect_format(str(t))[0] == "table"
    assert detect_format(str(junk))[0] is None
    assert {f["name"] for f in list_formats()} >= {"vamas", "phi_spe", "table"}


def test_unknown_format_error_is_bilingual(tmp_path):
    junk = tmp_path / "x.zzz"
    junk.write_bytes(bytes(range(256)))
    with pytest.raises(ReadError) as e:
        read_file(str(junk))
    assert "unknown file format" in str(e.value) and "无法识别" in e.value.zh
    with pytest.raises(ReadError):
        read_file(str(tmp_path / "missing.csv"))
    with pytest.raises(ReadError):
        read_file(str(junk), fmt="no_such_reader")


def test_broken_vamas_becomes_read_error(tmp_path):
    f = tmp_path / "bad.vms"
    f.write_text("VAMAS Surface Chemical Analysis Standard\nonly a header\n", encoding="utf-8")
    with pytest.raises(ReadError):
        read_file(str(f))


# ------------------------------------------------------------------ column templates
def _table(tmp_path, name="t.csv", kinetic=False, counts=False):
    x = np.arange(55.0, 70.0, 0.1)
    y = _peak(x)
    df = pd.DataFrame({"Kinetic energy" if kinetic else "Energy": (1486.6 - x) if kinetic else x,
                       "junk": np.arange(len(x)) * 0.0 + 7,
                       "Counts" if counts else "Ir": y * (2.0 if counts else 1.0)})
    p = tmp_path / name
    df.to_csv(p, index=False, encoding="utf-8")
    return str(p), x, y


def test_template_by_name_kinetic_and_regions(tmp_path):
    path, x, y = _table(tmp_path, kinetic=True)
    tpl = dict(base="table", x="Kinetic energy", y=["Ir"], energy="kinetic", hv=1486.6, regions={"Ir": "Ir 4f"})
    (s,) = read_file(path, template=tpl)
    assert s.region == "Ir 4f"
    np.testing.assert_allclose(s.be, x, atol=1e-9)
    np.testing.assert_allclose(s.cps, y, rtol=1e-12)
    assert s.acq_time() is None            # cps without a time: noise is estimated from the data


def test_template_counts_to_cps_and_poisson_time(tmp_path):
    path, x, y = _table(tmp_path, counts=True)
    (s,) = read_file(path, template=dict(base="table", x=0, y=[2], intensity="counts", acq_time=0.5))
    np.testing.assert_allclose(s.cps, 2 * y / 0.5)            # file holds counts = 2y
    assert s.acq_time() == 0.5
    np.testing.assert_allclose(s.counts(), 2 * y)             # counts recovered exactly
    (s1,) = read_file(path, template=dict(base="table", x=0, y=[2], intensity="counts"))
    assert s1.acq_time() == 1.0 and np.allclose(s1.counts(), 2 * y)


def test_template_errors(tmp_path):
    path, _, _ = _table(tmp_path)
    for bad in (dict(base="table"), dict(base="table", x="nope"), dict(base="table", x=9),
                dict(base="table", x=0, energy="kinetc"), dict(base="table", x=0, intensity="counts", acq_time=-1),
                dict(base="table", x=0, y=[0]), dict(base="table", x=0, colour="red")):
        with pytest.raises(ReadError):
            read_file(path, template=bad)


def test_excel_sheet_template(tmp_path):
    x = np.arange(525.0, 540.0, 0.1)
    p = tmp_path / "b.xlsx"
    with pd.ExcelWriter(p) as w:
        pd.DataFrame({"BE": x, "O": _peak(x, 531, 1.2)}).to_excel(w, sheet_name="O1s", index=False)
        pd.DataFrame({"BE": x, "X": _peak(x, 533, 1.2)}).to_excel(w, sheet_name="other", index=False)
    sps = read_file(str(p), template=dict(base="table", x="BE", y=["O"], sheet="O1s", regions={"O": "O 1s"}))
    assert [s.region for s in sps] == ["O 1s"]


def test_gbk_csv_header(tmp_path):
    x = np.arange(280.0, 292.0, 0.1)
    p = tmp_path / "gbk.csv"
    with open(p, "w", encoding="gb18030") as f:
        f.write("结合能,强度\n")
        for a, b in zip(x, _peak(x, 284.8)):
            f.write(f"{a:.2f},{b:.3f}\n")
    info = inspect_table(str(p))
    assert info[0]["names"] == ["结合能", "强度"]
    (s,) = read_file(str(p), template=dict(base="table", x="结合能", y=["强度"], regions={"强度": "C 1s"}))
    assert s.region == "C 1s" and len(s.be) == len(x)


def test_wizard_guess_build_try(tmp_path):
    path, x, _ = _table(tmp_path, kinetic=True, counts=True)
    (sh,) = inspect_table(path)
    g = sh["guess"]
    assert g["x"] == 0 and g["energy"] == "kinetic" and g["intensity"] == "counts" and 2 in g["y"]
    tpl = build_template(sh["names"], 0, [2], energy="kinetic", intensity="counts", acq_time=0.2,
                         regions={2: "Ir 4f"})
    assert tpl["x"] == "Kinetic energy" and tpl["y"] == ["Counts"] and tpl["regions"] == {"Counts": "Ir 4f"}
    (r,) = try_read(path, tpl)
    assert r["region"] == "Ir 4f" and r["acq_time"] == 0.2
    assert r["be_min"] == pytest.approx(x.min(), abs=1e-6)
    with pytest.raises(ReadError):
        build_template(sh["names"], 0, [0])
    with pytest.raises(ReadError):
        add_template({}, "table", tpl)          # built-in reader name


def test_duplicate_header_uses_column_number():
    tpl = build_template(["BE", "I", "BE", "I"], 2, [3])
    assert tpl["x"] == 2 and tpl["y"] == [3]


def test_project_template_roundtrip(tmp_path):
    path, x, y = _table(tmp_path, counts=True)
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_template("lab", dict(base="table", x="Energy", y=["Counts"], intensity="counts", acq_time=0.5,
                               regions={"Counts": "Ir 4f"}))
    keys = p.add_file(path, template="lab")
    assert keys == ["t/Ir 4f"]
    p2 = Project.open(p.path)
    s = p2.spectra["t/Ir 4f"]
    assert s.acq_time() == 0.5 and np.allclose(s.counts(), 2 * y)
    with pytest.raises(ReadError):
        p2.add_file(path, template="nope")
    assert schema.validate_project(p.path).ok


# ------------------------------------------------------------------ schema: models
def _m(**over):
    d = dict(region="Ir 4f", fit_range=[55, 70], background=dict(kind="shirley", lo=55, hi=70),
             components=[dict(name="Ir0", shape="gl", doublet=True,
                              params=dict(center=dict(value=60.9, min=60, max=62), fwhm=1.0, area=1000,
                                          split=dict(value=2.98, vary=False), ratio=dict(value=0.75, vary=False))),
                         dict(name="Ir4", shape="gl", doublet=True,
                              params=dict(center="Ir0.center + 1.6", fwhm="Ir0.fwhm", area=500,
                                          split=dict(value=2.98, vary=False), ratio=dict(value=0.75, vary=False)))])
    d.update(over)
    return d


def _errs(d, **kw):
    return schema.check_model(d, "m", **kw).errors()


def test_valid_model_is_clean():
    assert schema.check_model(_m(), "m").items == []


@pytest.mark.parametrize("mutate,needle", [
    (lambda d: d["components"][0]["params"].update(fwhm=dict(value=1, min=2, max=1)), "min 2 > max 1"),
    (lambda d: d["components"][0]["params"].update(fwmh=1.0), "free parameter not used"),
    (lambda d: d["components"][0].update(shape="lorenz"), "unknown line shape"),
    (lambda d: d["components"][1]["params"].update(center="Ir9.center + 1"), "unknown component 'Ir9'"),
    (lambda d: d["components"][1]["params"].update(center="Ir0.centre + 1"), "has no parameter 'centre'"),
    (lambda d: d["components"][1]["params"].update(center="__import__('os')"), "not allowed"),
    (lambda d: d["components"][1].update(name="Ir0"), "duplicate component"),
    (lambda d: d["components"][0]["params"].update(area=dict(value=1, min=0, max=0)), "min = max"),
    (lambda d: d["background"].update(kind="shirly"), "unknown background"),
    (lambda d: d["background"].update(lo=70, hi=55), "lo 70 ≥ hi 55"),
    (lambda d: d.update(fit_range=[3, 3]), "zero width"),
    (lambda d: d.update(weighting="sqrt"), "weighting"),
    (lambda d: d["components"][0].update(doublet=False), "needs \"doublet\": true"),
])
def test_model_errors(mutate, needle):
    d = _m()
    mutate(d)
    errs = _errs(d)
    assert any(needle in e for e in errs), errs


def test_circular_expressions_are_errors():
    d = _m()
    d["components"][0]["params"]["fwhm"] = "Ir4.fwhm * 1.0"         # Ir4.fwhm = Ir0.fwhm → cycle
    assert any("circular" in e for e in _errs(d))


def test_auxiliary_parameter_used_in_expression_is_fine():
    d = _m()
    d["components"][1]["params"]["shift"] = dict(value=1.6, min=1.0, max=2.4)
    d["components"][1]["params"]["center"] = "Ir0.center + Ir4.shift"
    assert schema.check_model(d, "m").items == []


def test_model_warnings_ratio_split_bounds():
    d = _m()
    d["components"][0]["params"]["ratio"] = dict(value=0.5, vary=False)
    d["components"][0]["params"]["split"] = dict(value=4.0, vary=False)
    d["components"][0]["params"]["center"] = dict(value=65, min=60, max=62)
    rep = schema.check_model(d, "m")
    assert rep.ok
    w = " ".join(rep.warnings())
    assert "theory" in w and "tabulated" in w and "outside [60, 62]" in w


def test_fit_range_must_overlap_data():
    from peakforge.spectrum import Spectrum
    x = np.arange(520.0, 540.0, 0.1)
    sp = Spectrum(region="Ir 4f", be=x, cps=_peak(x, 530))
    assert any("does not overlap" in e for e in _errs(_m(), spectrum=sp))
    assert _errs(_m(fit_range=[525, 535], background=dict(kind="shirley")), spectrum=sp) == []


def test_builtin_presets_validate_cleanly():
    import glob
    for f in glob.glob(os.path.join(presets.DATA, "presets", "*.json")):
        with open(f, encoding="utf-8") as fh:
            assert schema.check_preset(json.load(fh), os.path.basename(f)).items == [], f


def test_broken_project_preset_is_skipped(tmp_path):
    p = Project.create(str(tmp_path / "proj"), "t")
    bad = dict(id="bad", region="Ir 4f", components=[dict(name="A", shape="nope")])
    with open(os.path.join(p.root, "presets", "bad.json"), "w", encoding="utf-8") as f:
        json.dump(bad, f)
    with open(os.path.join(p.root, "presets", "broken.json"), "w", encoding="utf-8") as f:
        f.write("{not json")
    ids = presets.list_presets(p.root)
    assert "bad" not in ids and "broken" not in ids and "ir4f_metal_oxide" in ids
    rep = schema.validate_project(p.path)
    assert rep.n_err >= 2 and any("line 1" in e for e in rep.errors())


# ------------------------------------------------------------------ schema: project + wiring
def _proj_with_spectrum(tmp_path):
    x = np.arange(55.0, 70.0, 0.1)
    path = tmp_path / "s.csv"
    pd.DataFrame({"Binding energy": x, "Ir 4f": _peak(x)}).to_csv(path, index=False, encoding="utf-8")
    p = Project.create(str(tmp_path / "proj"), "t")
    (key,) = p.add_file(str(path))
    return p, key


def test_project_json_error_reports_line(tmp_path):
    p = Project.create(str(tmp_path / "proj"), "t")
    with open(p.path, "w", encoding="utf-8") as f:
        f.write('{"format": "peakforge-project",\n "files": [}\n')
    with pytest.raises(SchemaError) as e:
        Project.open(p.path)
    assert "line 2" in str(e.value)


def test_project_structure_errors(tmp_path):
    p = Project.create(str(tmp_path / "proj"), "t")
    p.data["files"] = [dict(path="data/raw/gone.csv", sample="S")]
    p.data["samples"] = {"S": dict(shift="a lot")}
    p.save()
    with pytest.raises(SchemaError) as e:
        Project.open(p.path)
    assert "samples.S.shift" in str(e.value)
    p.data["samples"] = {"S": dict(shift=0.0)}
    p.save()
    p2 = Project.open(p.path)                       # a missing raw file does not block opening
    assert any("file not found" in w for w in p2.validation.warnings())


def test_get_model_refuses_invalid_file(tmp_path):
    p, key = _proj_with_spectrum(tmp_path)
    m = p.new_model(key, "__generic__")
    p.set_model(key, m)
    rec = p.get_model_record(key)
    rec["model"]["components"][0]["shape"] = "nope"
    with open(p._model_path(key), "w", encoding="utf-8") as f:
        json.dump(rec, f)
    with pytest.raises(SchemaError) as e:
        p.get_model(key)
    assert "models/" in str(e.value) and "unknown line shape" in str(e.value)
    assert schema.validate_project(p.path).n_err == 1


def test_ops_set_model_validates_against_spectrum(tmp_path):
    p, key = _proj_with_spectrum(tmp_path)
    with pytest.raises(SchemaError):
        ops.set_model(p, key, _m(fit_range=[500, 510]))
    out = ops.set_model(p, key, _m(fit_range=[55, 69.9], background=dict(kind="shirley")))
    assert out["ok"] and isinstance(out["warnings"], list)


def test_cli_validate_exit_code(tmp_path, capsys):
    from peakforge.cli import main
    p, key = _proj_with_spectrum(tmp_path)
    assert main(["validate", p.path]) == 0
    with open(p._model_path(key), "w", encoding="utf-8") as f:
        json.dump(dict(model=dict(components=[dict(name="1bad")])), f)
    assert main(["validate", p.path]) == 1
    assert "must be an identifier" in capsys.readouterr().out


# ------------------------------------------------------------------ logs
def test_diagnostics_zip_has_no_raw_data(tmp_path):
    p, key = _proj_with_spectrum(tmp_path)
    p.set_model(key, p.new_model(key, "__generic__"))
    logs.log.warning("test entry")
    z = logs.diagnostics_zip(tmp_path / "d.zip", p)
    with zipfile.ZipFile(z) as zf:
        names = zf.namelist()
        env = json.loads(zf.read("environment.json"))
    assert "environment.json" in names and "validate.txt" in names
    assert any(n.startswith("project/models/") for n in names)
    assert not any("data/raw" in n or n.endswith(".csv") for n in names)
    assert env["peakforge"] and env["python"]


def test_excepthook_logs(monkeypatch):
    seen = []
    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)
    logs.install_excepthook(seen.append)
    try:
        raise RuntimeError("boom-for-test")
    except RuntimeError:
        sys.excepthook(*sys.exc_info())
    assert seen and "boom-for-test" in seen[0]
