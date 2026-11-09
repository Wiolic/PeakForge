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


def region(lo, hi, peaks, base=800.0, step=400.0, counts=6.0, seed=0):
    rng = np.random.default_rng(seed)
    x = np.arange(lo, hi + 1e-9, 0.1)
    y = np.zeros_like(x)
    for shape, c, w, a, kw, split, ratio in peaks:
        y += a * lineshapes.profile(shape, x, c, w, **kw)
        if split:
            y += a * ratio * lineshapes.profile(shape, x, c + split, w, **kw)
    cum = np.cumsum(y)
    y = y + base + step * cum / cum[-1]
    return x[::-1], rng.poisson(y * counts)[::-1] / counts


def sample(oxidised: float, seed: int):
    gl = dict(m=0.3)
    return {
        "C 1s": region(280, 292, [("gl", 284.8, 1.2, 9000, gl, None, None), ("gl", 286.3, 1.2, 1800, gl, None, None),
                                  ("gl", 288.8, 1.2, 900, gl, None, None)], seed=seed),
        "O 1s": region(524, 538, [("gl", 530.0, 1.3, 9000 * oxidised + 1500, gl, None, None),
                                  ("gl", 531.5, 1.4, 6000, gl, None, None), ("gl", 532.9, 1.4, 2000, gl, None, None)],
                       base=2500, step=900, seed=seed + 1),
        "Ir 4f": region(55, 75, [("ds", 60.9, 0.5, 30000 * (1 - oxidised), dict(alpha=0.12, gamma=0.4), 2.98, 0.75),
                                 ("pvoigt", 61.8, 1.2, 30000 * oxidised, dict(eta=0.3), 2.98, 0.75),
                                 ("pvoigt", 62.6, 1.2, 9000, dict(eta=0.3), 2.98, 0.75)],
                        base=3000, step=2500, seed=seed + 2),
        "Ti 2p": region(450, 470, [("gl", 458.8, 1.2, 12000, gl, 5.7, 0.5),
                                   ("gl", 457.3, 1.3, 2500 * (1 - oxidised), gl, 5.7, 0.5)],
                        base=4000, step=1500, seed=seed + 3),
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
write(os.path.join(OUT, "demo_fresh.csv"), sample(0.35, 1))
write(os.path.join(OUT, "demo_aged.csv"), sample(0.75, 11))
print("written to", os.path.abspath(OUT))
