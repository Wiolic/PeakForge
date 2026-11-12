"""Smoke test of the packaged app (run by build.ps1 and the release workflow; also fine against a pip install).

Usage:  python packaging/smoke.py dist/PeakForge        (folder containing peakforge-cli.exe and PeakForge.exe)

Checks: --version, selftest (GUI + help pages + package data, offscreen), formats, a synthetic-spectrum fit compared
with the reference values from the source environment, validate, PNG/Excel/Origin-script export, diagnostics bundle,
agent-config pointing at peakforge-cli.exe, and an MCP `initialize` round trip over stdio.
Exit code 0 only if everything passes.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Reference: examples/demo_fresh.csv, O 1s, generic 3-component preset, 1 start (source environment, 2026-11).
REF = {"O_lat": dict(center=530.145, fwhm=1.329, fraction=43.92),
       "O_OH": dict(center=531.355, fwhm=1.329, fraction=41.26),
       "O_H2O": dict(center=532.513, fwhm=1.329, fraction=14.82)}
TOL = dict(center=0.05, fwhm=0.05, fraction=1.0)


def main() -> int:
    dist = Path(sys.argv[1] if len(sys.argv) > 1 else "dist/PeakForge").resolve()
    cli = dist / ("peakforge-cli.exe" if os.name == "nt" else "peakforge-cli")
    if not cli.exists():
        print(f"not found: {cli}")
        return 2
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    env.pop("PYTHONUTF8", None)             # the packaged app must not depend on it (UTF-8 mode is set in the spec)
    env.pop("PYTHONIOENCODING", None)
    fails: list[str] = []

    def run(*args: str, timeout: float = 300, ok: bool = True) -> subprocess.CompletedProcess:
        r = subprocess.run([str(cli), *args], capture_output=True, text=True, encoding="utf-8", errors="replace",
                           env=env, timeout=timeout, check=False)
        if ok and r.returncode != 0:
            fails.append(f"{' '.join(args)} -> exit {r.returncode}\n{(r.stdout + r.stderr)[-1500:]}")
        return r

    def check(cond: bool, msg: str) -> None:
        print(("  ok   " if cond else "  FAIL ") + msg)
        if not cond:
            fails.append(msg)

    print("== version / selftest")
    v = run("--version")
    check("PeakForge" in v.stdout, f"--version: {v.stdout.strip()}")
    st = run("selftest", timeout=600)
    check("selftest: ok" in st.stdout, "selftest (GUI, help pages, package data)")
    fm = run("formats")
    check("vamas" in fm.stdout.lower() or "spe" in fm.stdout.lower(), "formats lists readers")

    with tempfile.TemporaryDirectory(prefix="peakforge smoke ") as tmp:          # a space in the path on purpose
        proj = Path(tmp) / "smoke"
        print("== project / fit")
        run("init", str(proj), "--name", "smoke")
        xp = str(next(proj.glob("*.xpsproj")))
        run("add", xp, str(ROOT / "examples" / "demo_fresh.csv"))
        key = "demo_fresh/O 1s"
        run("preset", xp, key)
        fit = run("fit", xp, key, "--starts", "1")
        try:
            res = json.loads(fit.stdout)[0]
            check(res.get("ok") is True, "fit converged")
            comps = {c["component"]: c for c in res["components"]}
            for name, ref in REF.items():
                for what, tol in TOL.items():
                    got = comps[name][what]
                    check(abs(got - ref[what]) <= tol, f"{name}.{what} = {got:.3f} (reference {ref[what]} ± {tol})")
        except (ValueError, KeyError, IndexError) as e:
            check(False, f"fit output not understood: {e}\n{fit.stdout[-800:]}")
        val = run("validate", xp)
        check("0 error(s)" in val.stdout, "validate: no errors")

        print("== export")
        out = Path(tmp) / "out"
        run("export", xp, "--formats", "png", "xlsx", "origin", "--out", str(out))
        check(any(out.rglob("*.png")), "PNG written")
        check(any(out.rglob("*.xlsx")), "Excel written")
        check((out / "build_origin.py").exists() or any(out.rglob("build_origin.py")),
              "Origin fallback script written (origin_builder.py is packaged)")

        print("== diagnostics / agent")
        dg = run("diag", xp, "--out", str(Path(tmp) / "diag.zip"))
        zp = Path(tmp) / "diag.zip"
        if zp.exists():
            names = zipfile.ZipFile(zp).namelist()
            check(not any(n.startswith("data/raw") or n.lower().endswith((".spe", ".vms")) for n in names),
                  "diagnostics bundle holds no raw data")
        else:
            check(False, f"diagnostics bundle not written\n{dg.stdout[-500:]}")
        ac = run("agent-config")
        check("peakforge-cli" in ac.stdout, "agent-config points at peakforge-cli")

    print("== MCP stdio")
    msg = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                      "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "smoke", "version": "0"}}})
    p = subprocess.Popen([str(cli), "mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    try:
        p.stdin.write((msg + "\n").encode("utf-8"))
        p.stdin.flush()
        line = p.stdout.readline().decode("utf-8", "replace")
        check('"serverInfo"' in line or '"protocolVersion"' in line, "MCP server answers initialize")
    finally:
        p.kill()

    if fails:
        print("\nSMOKE TEST FAILED:")
        for f in fails:
            print(" -", f)
        return 1
    print("\nsmoke test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
