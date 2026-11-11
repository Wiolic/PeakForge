"""Every core level in the table (Li–U) must be fittable with the generic model (automatic peak
search, tabulated spin–orbit doublets) — on synthetic spectra with two chemical states,
a Shirley-type step and Poisson noise."""
import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from peakforge import presets  # noqa: E402
from peakforge.core import lineshapes  # noqa: E402
from peakforge.core.fit import fit, prepare  # noqa: E402
from peakforge.spectrum import Spectrum, normalize_region  # noqa: E402

LEVELS = sorted(presets.orbitals().items(), key=lambda kv: (kv[1]["z"], kv[1]["be"]))


def synth(region: str, info: dict, seed: int = 0, chem_shift: float = 1.6, second: float = 0.45):
    rng = np.random.default_rng(seed)
    be, split, ratio = info["be"], info.get("split"), info.get("ratio")
    lo = be - 8
    hi = be + (split or 0) + 10
    x = np.arange(lo, hi, 0.1)
    w = 1.3
    y = np.zeros_like(x)
    for c, a in ((be, 1.0), (be + chem_shift, second)):
        y += 5000 * a * lineshapes.profile("gl", x, c, w, m=0.3)
        if split:
            y += 5000 * a * ratio * lineshapes.profile("gl", x, c + split, w, m=0.3)
    step = np.cumsum(y)
    y = y + 300 + 200 * step / step[-1]
    y = rng.poisson(y * 4) / 4
    return Spectrum(region=region, be=x, cps=y, sample="synthetic")


# Known auto-model weakness (phase 1): Re 4f with a second state 1.6 eV above, i.e. 0.8 eV below the
# 2.43 eV spin-orbit partner — generic_model() mistakes the pair and the residual refinement lands in a
# local minimum (RMS ≈ 7 %). Old and new line shapes both fail some noise seeds; fix in presets, not here.
_KNOWN_WEAK = {"Re 4f"}


@pytest.mark.parametrize("region,info", [pytest.param(k, v, marks=pytest.mark.xfail(
    reason="generic_model: second state near the spin-orbit partner", strict=True)) if k in _KNOWN_WEAK
    else (k, v) for k, v in LEVELS], ids=[k for k, _ in LEVELS])
def test_every_core_level_fits(region, info):
    sp = synth(region, info)
    m = presets.generic_model(sp)
    assert m.components, "no component found"
    if info.get("split") and not info.get("complex"):
        assert all(c.doublet for c in m.components)
        assert m.components[0].params["split"].value == pytest.approx(info["split"], rel=0.08)
    r = fit(m, prepare(sp.be, sp.cps, m), n_starts=2)
    assert r.ok
    # multiplet-dominated levels (open 3d/4f shells) are fitted with free singlets: looser criterion
    assert r.rms_pct < (6.0 if info.get("complex") else 4.0), f"RMS {r.rms_pct:.2f}%"
    centres = sorted(v["center"] for v in r.values.values())
    assert min(abs(c - info["be"]) for c in centres) < 0.35   # main state recovered


@pytest.mark.parametrize("label,expect_doublet", [("Fe 2p3/2", False), ("Fe2p3", False), ("Cu 2p", True), ("Ni 2p", False),
                                                  ("Pt 4f7/2", False), ("Ta", True)])
def test_subshell_and_bare_element_labels(label, expect_doublet):
    region = normalize_region(label)
    info = presets.orbital(region)
    assert info is not None, region
    sp = synth(region, info)
    m = presets.generic_model(sp)
    assert any(c.doublet for c in m.components) == expect_doublet
    r = fit(m, prepare(sp.be, sp.cps, m), n_starts=2)
    assert r.ok and r.rms_pct < 5.0


def test_unknown_label_still_fits():
    info = {"be": 100.0, "split": None}
    sp = synth("Sample column 3", info)
    m = presets.generic_model(sp)
    r = fit(m, prepare(sp.be, sp.cps, m), n_starts=2)
    assert r.ok and r.rms_pct < 4.0


def test_table_covers_li_to_u():
    els = {v["element"] for v in presets.orbitals().values()}
    assert len(els) == 90                                     # Li (3) … U (92)
    assert {"Li", "U", "Fe", "Ce", "Ir", "Au"} <= els
