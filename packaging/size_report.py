"""Size audit of the packaged app: lists the entries under _internal, writes build/size_report.csv, compares with the last run.

Usage (repo root):  python packaging/size_report.py [dist/PeakForge] [--limit-mb 400] [--forbid mkl pyarrow ...]
Exit code 1 when the unpacked size exceeds --limit-mb, a forbidden package shows up or direct_url.json leaked in
(used by build.ps1 as the size guard). Not part of the installed software.
"""
import argparse
import csv
import re
import sys
from pathlib import Path

DEFAULT_FORBID = ["mkl", "mkl_fft", "pyarrow", "botocore", "boto3", "sklearn", "skimage", "plotly", "mypy",
                  "originpro", "pytest"]          # keep in sync with excludes in peakforge.spec


def tree_size(p: Path) -> int:
    if p.is_file():
        return p.stat().st_size
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def collect(root: Path):
    internal = root / "_internal"
    base = internal if internal.is_dir() else root
    rows, mkl = {}, 0
    for e in base.iterdir():
        s = tree_size(e)
        if re.match(r"mkl_.*\.dll$", e.name, re.I):
            mkl += s
        else:
            rows[e.name] = s
    if mkl:
        rows["mkl_*.dll"] = mkl
    return rows, base


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dist", nargs="?", default="dist/PeakForge")
    ap.add_argument("--limit-mb", type=float, default=None)
    ap.add_argument("--forbid", nargs="*", default=DEFAULT_FORBID)
    ap.add_argument("--out", default="build/size_report.csv")
    ap.add_argument("--top", type=int, default=25)
    a = ap.parse_args()

    root = Path(a.dist)
    if not root.is_dir():
        print(f"not found: {root}")
        return 2
    rows, base = collect(root)
    total_mb = sum(tree_size(f) for f in root.iterdir()) / 1e6

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    prev, prev_total = {}, 0.0
    if out.exists():
        with open(out, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r["name"] == "TOTAL":
                    prev_total = float(r["mb"])
                else:
                    prev[r["name"]] = float(r["mb"])

    items = sorted(rows.items(), key=lambda kv: -kv[1])
    print(f"{root}  total {total_mb:.0f} MB" + (f" (last {prev_total:.0f} MB, {total_mb - prev_total:+.0f})" if prev_total else ""))
    for name, s in items[:a.top]:
        mb = s / 1e6
        d = f"  ({mb - prev[name]:+.1f})" if name in prev else ""
        print(f"  {mb:8.1f} MB  {name}{d}")
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["name", "mb"])
        w.writerow(["TOTAL", f"{total_mb:.1f}"])
        for name, s in items:
            w.writerow([name, f"{s / 1e6:.2f}"])
    print(f"written {out}")

    bad = []
    for e in base.iterdir():
        stem = e.name.lower().split(".")[0]
        for fb in a.forbid:
            fb = fb.lower()
            if stem == fb or stem.startswith(fb + "_") or (fb == "mkl" and stem.startswith("mkl")):
                bad.append(e.name)
                break
    code = 0
    leaked = [str(f.relative_to(root)) for f in root.rglob("direct_url.json")]
    if leaked:
        print("FAIL: direct_url.json in the package: " + ", ".join(leaked))
        code = 1
    if bad:
        print("FAIL: forbidden entries " + ", ".join(sorted(set(bad))))
        code = 1
    if a.limit_mb and total_mb > a.limit_mb:
        print(f"FAIL: {total_mb:.0f} MB exceeds the limit {a.limit_mb:.0f} MB")
        code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
