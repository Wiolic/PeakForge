"""Colour model (phase 3.6 A): base colour -> series, combos, per-figure overrides, migration, export consistency."""
import itertools
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from peakforge.export import themes as T  # noqa: E402

EX = os.path.join(os.path.dirname(__file__), "..", "examples")


@pytest.mark.parametrize("base", list(T.BASE_COLORS))
@pytest.mark.parametrize("mode", T.MODES)
def test_series_distinct_in_gamut_deterministic(base, mode):
    for n in range(1, 9):
        cs = T.series(base, n, mode)
        assert len(cs) == n and cs == T.series(base, n, mode)
        assert all(0 <= v <= 255 for c in cs for v in c)
        for a, b in itertools.combinations(cs, 2):
            assert T.delta_e(a, b) >= 0.05, (base, n, mode)


def test_series_neighbours_contrast_more_than_gradient_neighbours():
    cs = T.series("azure", 8, "series")
    gr = T.series("azure", 8, "gradient")
    near = min(T.delta_e(cs[i], cs[i + 1]) for i in range(7))
    assert near > min(T.delta_e(gr[i], gr[i + 1]) for i in range(7))


def test_oklch_roundtrip():
    for rgb in [(200, 100, 50), (10, 160, 140), (120, 120, 120)]:
        assert max(abs(a - b) for a, b in zip(T.oklch_to_rgb(*T.rgb_to_oklch(rgb)), rgb)) <= 1


def test_combos_use_known_bases_and_are_distinct():
    for cid, c in T.COMBOS.items():
        assert set(c["bases"]) <= set(T.BASE_COLORS), cid
        assert len(set(c["bases"])) == len(c["bases"])
    assert set(T.LEGACY_COMBO.values()) <= set(T.COMBOS)


def test_same_element_same_base_and_c_o_fixed():
    pal = dict(combo="canyon")
    regs = ["Ir 4f", "O 1s", "C 1s", "Co 2p"]
    a = T.resolve_base(pal, "Ir 4f", regs)
    assert a == T.resolve_base(pal, "Ir 4f", regs[::-1])          # independent of order of discovery
    assert T.resolve_base(pal, "C 1s", regs) == "graphite" and T.resolve_base(pal, "O 1s", regs) == "slate"
    assert T.resolve_base(pal, "Co 2p", regs) != a
    assert T.resolve_base(dict(combo="canyon", assign={"Ir": "rose"}), "Ir 4f", regs) == "rose"


def test_figure_override_and_manual_colors():
    pal = dict(combo="glacier", figures={"s/Ir 4f": dict(base="amber", mode="gradient")})
    th = T.resolve_theme(pal, "s/Ir 4f", "Ir 4f", ["Ir 4f"], 4)
    assert th["components"] == T.series("amber", 4, "gradient")
    assert T.resolve_theme(pal, "other", "Ir 4f", ["Ir 4f"], 4)["components"] != th["components"]
    man = dict(combo="glacier", figures={"k": dict(colors=["#112233", "#445566"])})
    assert T.resolve_theme(man, "k", "Ir 4f", [], 3)["components"][:2] == [(17, 34, 51), (68, 85, 102)]


def test_legacy_ids_migrate():
    for old in ("glacier", "fjord", "lagoon", "badlands", "prairie", "warm", "no_such"):
        assert T.theme_id(old) in T.COMBOS
    assert T.legacy_palette("canyon")["combo"] == "canyon"
    assert T.theme("lagoon")["components"]                     # an old id is still a usable theme name


def _project(tmp_path):
    from peakforge.project import Project
    p = Project.create(str(tmp_path / "proj"), "t")
    p.add_file(os.path.join(EX, "demo_fresh.csv"))
    p.add_file(os.path.join(EX, "demo_aged.csv"))
    for k in p.keys(narrow_only=True):
        p.set_model(k, p.new_model(k))
        p.fit(k, n_starts=1)
    return p


def test_old_project_opens_with_mapped_combo(tmp_path):
    import json
    from peakforge.project import Project
    p = _project(tmp_path)
    d = json.load(open(p.path, encoding="utf-8"))
    d["settings"].pop("palette", None)
    d["settings"]["theme"] = "badlands"
    json.dump(d, open(p.path, "w", encoding="utf-8"))
    q = Project.open(p.path)
    assert q.palette()["combo"] == "canyon"
    k = q.keys(narrow_only=True)[0]
    assert q.figure_theme(k)["components"]


def test_schema_warns_on_unknown_ids(tmp_path):
    from peakforge import schema
    p = _project(tmp_path)
    k = p.keys(narrow_only=True)[0]
    p.settings["palette"] = dict(combo="nope", assign={"Ir": "puce"}, figures={k: dict(base="x", mode="y", colors=["red"])})
    p.save()
    rep = schema.validate_project(p.path)
    txt = rep.text() if hasattr(rep, "text") else str(rep)
    assert not rep.errors() and "puce" in txt and "'nope'" in txt and "'x'" in txt
    p.settings["palette"] = "bad"
    p.save()
    assert schema.validate_project(p.path).errors()


def test_exports_use_project_colours(tmp_path):
    import pandas as pd
    from peakforge.export.exporter import collect_export, run_export
    from peakforge.export.themes import comp_color, to_hex
    p = _project(tmp_path)
    k0, k1 = p.keys("O 1s")[:2]
    p.set_figure_color(k0, base="amber")
    job = collect_export(p, None, str(tmp_path / "e"), None, ("png", "xlsx", "origin"), 60)
    snap = job["snap"]
    assert snap["themes"][k0]["components"] == T.series("amber", len(p.get_model(k0).components))
    assert snap["themes"][k1]["components"] != snap["themes"][k0]["components"]
    r = run_export(job)
    df = pd.read_excel(r["xlsx"], sheet_name="Colours")
    m0 = p.get_model(k0)
    want = [to_hex(comp_color(snap["themes"][k0], i, c.color)) for i, c in enumerate(m0.components)]
    got = df[(df.Sample == p.sample_label(p.spectra[k0].sample)) & (df.Region == "O 1s")]["Colour"].tolist()[:len(want)]
    assert got == want
    import json
    spec = json.load(open(tmp_path / "e" / "origin" / "spec.json", encoding="utf-8"))
    assert [tuple(c) for c in spec["graphs"][0]["colors"]["comp"]] == snap["themes"][snap["items"][0][0]]["components"]
    # explicit theme overrides everything (per-figure included)
    job2 = collect_export(p, None, str(tmp_path / "e2"), "dusk", ("png",), 60)
    assert job2["snap"]["themes"][k0]["components"] != snap["themes"][k0]["components"]


def test_gui_canvas_matches_export(tmp_path):
    pytest.importorskip("PySide6")
    import matplotlib
    matplotlib.use("QtAgg")
    from PySide6.QtWidgets import QApplication
    from peakforge.gui.main_window import MainWindow
    app = QApplication.instance() or QApplication([])  # noqa: F841
    p = _project(tmp_path)
    k = p.keys("O 1s")[0]
    p.set_figure_color(k, base="teal")
    w = MainWindow(p.path)
    w.select_key(k)
    assert w.view.theme["components"] == p.figure_theme(k, len(w.model.components))["components"]
    w.set_theme("dusk")                            # applies to all figures, drops per-figure choices
    assert "figures" not in w.project.palette() or not w.project.palette()["figures"]
    assert w.project.palette()["combo"] == "dusk"
    assert w.view.theme["components"] == w.project.figure_theme(k, len(w.model.components))["components"]
    w.close()


def test_figure_color_dialog_values(tmp_path):
    pytest.importorskip("PySide6")
    from PySide6.QtWidgets import QApplication
    from peakforge.gui.palette import FigureColorDialog
    app = QApplication.instance() or QApplication([])  # noqa: F841
    p = _project(tmp_path)
    k = p.keys("O 1s")[0]
    d = FigureColorDialog(p, k, 3)
    assert d.values() == dict(base=None, mode=None)
    d._pick("rose")
    d.mode.setCurrentIndex(1)
    assert d.values() == dict(base="rose", mode="gradient")
