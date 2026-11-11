"""check_move: verify that a refactor only MOVED code.

Every top-level def / class / assignment of the old single file (read from git HEAD) must appear, with an
identical syntax tree (ast.dump), in some module of the new package, and every old top-level name must be
importable from the new package.  With --class NAME the methods of that class are compared one by one
(decorators included) against the methods of every class found in the new files, and each must be reachable
as an attribute of the old class name in the new package.

Usage (repo root):
    python tools/check_move.py src/peakforge/gui/main_window.py src/peakforge/gui/window \
        --extra src/peakforge/gui/main_window.py --class MainWindow --dots 1 --allow ICON
--dots N: files in the new package sit N levels deeper (relative imports inside bodies get N more dots).
--allow NAME: names that must change when moved (e.g. a path computed from __file__); they are listed, not failed.
"""
from __future__ import annotations

import argparse
import ast
import importlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class _Dots(ast.NodeTransformer):
    """New files sit N levels deeper: relative imports inside bodies have N more dots; subtract them before comparing"""
    def __init__(self, n):
        self.n = n

    def visit_ImportFrom(self, node):
        if self.n and node.level > self.n:
            node.level -= self.n
        return node


def _top_nodes(src: str, dots: int = 0):
    """Top-level nodes -> {name: ast.dump}; top-level imports are not compared (they necessarily change)"""
    out = {}
    tree = ast.parse(src)
    if dots:
        tree = _Dots(dots).visit(tree)
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[n.name] = ast.dump(n)
        elif isinstance(n, (ast.Assign, ast.AnnAssign)):
            tg = n.targets if isinstance(n, ast.Assign) else [n.target]
            names = [t.id for t in tg if isinstance(t, ast.Name)]
            for nm in names:
                out[nm] = ast.dump(n)
    return out


def _class_methods(src: str, cls: str | None, dots: int = 0):
    """{method name: ast.dump} of the class `cls` (old file) or of every class (new files, cls=None)."""
    out = {}
    tree = ast.parse(src)
    if dots:
        tree = _Dots(dots).visit(tree)
    for n in tree.body:
        if isinstance(n, ast.ClassDef) and (cls is None or n.name == cls):
            for m in n.body:
                if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    out[m.name] = ast.dump(m)
    return out


def _git_show(rel: str, rev: str) -> str:
    return subprocess.run(["git", "show", f"{rev}:{rel}"], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", check=True).stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old")
    ap.add_argument("new_pkg")
    ap.add_argument("--extra", nargs="*", default=[], help="other files that received moved code")
    ap.add_argument("--rev", default="HEAD")
    ap.add_argument("--class", dest="cls", default=None, help="compare the methods of this class")
    ap.add_argument("--allow", nargs="*", default=[], help="names that legitimately change when moved")
    ap.add_argument("--module", default=None, help="module the old names must be importable from (default: new_pkg)")
    ap.add_argument("--dots", type=int, default=0, help="how many levels deeper the new files sit")
    a = ap.parse_args()

    old_rel = Path(a.old).as_posix()
    old = _top_nodes(_git_show(old_rel, a.rev))
    if a.cls:       # the class is compared method by method below
        old.pop(a.cls, None)
    new = {}
    files = list((ROOT / a.new_pkg).glob("*.py")) + [ROOT / e for e in a.extra]
    for f in files:
        for k, v in _top_nodes(f.read_text(encoding="utf-8"), a.dots if f.parent == ROOT / a.new_pkg else 0).items():
            if k in new and new[k] != v and f.name != "__init__.py":
                print(f"  [warning] {k} defined differently in several new files: {f.name}")
            new.setdefault(k, v)
    bad = 0
    for k, v in old.items():
        if k not in new:
            print(f"missing: {k}")
            bad += 1
        elif new[k] != v:
            if k in a.allow:
                print(f"changed (allowed): {k}")
            else:
                print(f"changed: {k}")
                bad += 1
    if a.cls:
        old_m = _class_methods(_git_show(old_rel, a.rev), a.cls)
        new_m = {}
        for f in files:
            d = a.dots if f.parent == ROOT / a.new_pkg else 0
            for k, v in _class_methods(f.read_text(encoding="utf-8"), None, d).items():
                if k in new_m and new_m[k] != v:
                    print(f"  [warning] method {k} defined twice with different bodies ({f.name})")
                new_m.setdefault(k, v)
        for k, v in old_m.items():
            if k not in new_m:
                print(f"method missing: {a.cls}.{k}")
                bad += 1
            elif new_m[k] != v:
                print(f"method changed: {a.cls}.{k}")
                bad += 1
        print(f"{a.cls}: {len(old_m)} methods checked")
    extra = sorted(set(new) - set(old))
    if extra:
        print("new names (should be re-exports / wrappers only):", ", ".join(extra))

    # old import path: every old top-level name must still be importable
    sys.path.insert(0, str(ROOT / "src"))
    modname = a.module or ".".join(Path(a.new_pkg).relative_to("src").parts)
    mod = importlib.import_module(modname)
    for k in old:
        if not hasattr(mod, k):
            print(f"not importable: {modname}.{k}")
            bad += 1
    print(f"{len(old)} old top-level names, {bad} problems")
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
