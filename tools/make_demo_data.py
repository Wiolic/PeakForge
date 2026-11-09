"""Synthetic demo data for the README / first-time users (no real measurement data in the repo).

examples/demo_fresh.csv, examples/demo_aged.csv — column pairs (BE, intensity) for
C 1s, O 1s, Ir 4f, Ti 2p; 'aged' is more oxidised. Run:  python tools/make_demo_data.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from peakforge.core import lineshapes  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "examples")


def region(lo, hi, peaks, base=800.0, step=0.05, counts=2.0, seed=0):
    rng = np.random.default_rng(seed)
    x = np.arange(lo, hi + 1e-9, 0.1)
    y = np.zeros_like(x)
    for shape, c, w, a, kw, split, ratio in peaks:
        y += a * lineshapes.profile(shape, x, c, w, **kw)
        if split:
            y += a * ratio * lineshapes.profile(shape, x, c + split, w, **kw)
    cum = np.cumsum(y)
    tot = np.trapezoid(y, x)
    slope = 0.004 * (x - lo) * base                     # gentle rise towards high BE
    y = y + base + slope + step * tot * cum / cum[-1]   # Shirley-like step ∝ peak area
    return x[::-1], rng.poisson(y * counts)[::-1] / counts


def sample(state: str, seed: int):
    """Realistic parameters: 'fresh' = mostly metallic Ir with an oxide shoulder,
    'aged' = mostly oxidised Ir (broad doublet + oxide satellite)."""
    gl = dict(m=0.3)
    pv = dict(eta=0.3)
    ds = dict(alpha=0.12, gamma=0.35)
    fresh = state == "fresh"
    ir0, ir4, ir3, sat = (24000, 7000, 4000, 1200) if fresh else (3000, 22000, 9000, 3500)
    lat, oh, h2o = (5000, 6000, 2000) if fresh else (2500, 7000, 4000)
    return {
        "C 1s": region(280, 292, [("gl", 284.8, 1.3, 9000, gl, None, None),
                                  ("gl", 286.3, 1.3, 1800, gl, None, None),
                                  ("gl", 288.7, 1.3, 700, gl, None, None)],
                       base=1500, step=0.03, counts=2, seed=seed),
        "O 1s": region(524, 540, [("gl", 530.1, 1.25, lat, gl, None, None),
                                  ("gl", 531.3, 1.45, oh, gl, None, None),
                                  ("gl", 532.5, 1.5, h2o, gl, None, None)],
                       base=3000, step=0.05, counts=2, seed=seed + 1),
        "Ir 4f": region(55, 75, [("ds", 60.85, 0.55, ir0, ds, 2.98, 0.75),
                                 ("pvoigt", 61.65, 1.05, ir4, pv, 2.98, 0.75),
                                 ("pvoigt", 62.4, 1.05, ir3, pv, 2.98, 0.75),
                                 ("gaussian", 66.8, 2.6, sat, {}, None, None)],
                        base=2500, step=0.06, counts=2, seed=seed + 2),
        "Ti 2p": region(450, 470, [("gl", 458.8, 1.05, 12000, gl, 5.7, 0.5),
                                   ("gl", 457.4, 1.2, 1800 if fresh else 400, gl, 5.7, 0.5)],
                        base=4000, step=0.04, counts=2, seed=seed + 3),
    }


def write(path, regions):
    cols, heads1, heads2 = [], [], []
    n = max(len(x) for x, _ in regions.values())
    for name, (x, y) in regions.items():
        pad = lambda a: np.r_[a, [np.nan] * (n - len(a))]   # noqa: E731
        cols += [pad(x), pad(y)]
        heads1 += [name, ""]
        heads2 += ["Binding energy (eV)", "Intensity (cps)"]
    arr = np.column_stack(cols)
    with open(path, "w", encoding="utf-8") as f:
        f.write(",".join(heads1) + "\n" + ",".join(heads2) + "\n")
        for row in arr:
            f.write(",".join("" if np.isnan(v) else f"{v:.3f}" for v in row) + "\n")


os.makedirs(OUT, exist_ok=True)
write(os.path.join(OUT, "demo_fresh.csv"), sample("fresh", 1))
write(os.path.join(OUT, "demo_aged.csv"), sample("aged", 11))
print("written to", os.path.abspath(OUT))
