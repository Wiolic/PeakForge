r"""Which third-party packages are really imported: runs pytest and writes the top-level package names found in
sys.modules at exit to build/used_modules.txt (+ installed-but-unused list in build/unused_installed.txt).
The exclude list in peakforge.spec may only be extended based on this (and a check that the package is not
imported lazily at run time). Only paths the tests exercise are covered.

Usage (repo root):  python packaging/used_modules.py
"""
import atexit
import os
import sys
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "used_modules.txt"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def dump() -> None:
    stdlib = set(getattr(sys, "stdlib_module_names", ()))
    used = sorted({m.split(".")[0] for m in sys.modules if not m.startswith("_")} - stdlib)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(used) + "\n", encoding="utf-8")
    top = {}
    for d in metadata.distributions():
        tl = (d.read_text("top_level.txt") or "").split()
        for t in tl or [d.metadata["Name"].replace("-", "_")]:
            top[t] = d.metadata["Name"]
    unused = sorted(t for t in top if t not in used and not t.startswith("_") and "." not in t)
    (OUT.parent / "unused_installed.txt").write_text("\n".join(f"{t}\t{top[t]}" for t in unused) + "\n", encoding="utf-8")
    print(f"\n{len(used)} top-level packages used -> {OUT}\n{len(unused)} installed but unused -> {OUT.parent / 'unused_installed.txt'}")


if __name__ == "__main__":
    atexit.register(dump)
    sys.path.insert(0, str(ROOT / "src"))
    import pytest
    sys.exit(int(pytest.main(["-q", "-x", str(ROOT / "tests")])))
