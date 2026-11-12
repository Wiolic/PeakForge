"""Agent connection helpers: MCP client configuration snippets and project AGENTS.md."""
from __future__ import annotations

import os
import shutil
import sys


def server_command() -> list[str]:
    """Absolute command so agents find PeakForge even when it is not on PATH (installer venv)."""
    here = os.path.dirname(sys.executable)
    if getattr(sys, "frozen", False):               # packaged app: the console executable next to PeakForge.exe
        return [os.path.join(here, "peakforge-cli.exe"), "mcp"]
    for cand in (os.path.join(here, "peakforge.exe"), os.path.join(here, "Scripts", "peakforge.exe")):
        if os.path.exists(cand):
            return [cand, "mcp"]
    exe = shutil.which("peakforge")
    if exe:
        return [exe, "mcp"]
    py = sys.executable
    if py.lower().endswith("pythonw.exe"):          # GUI runs under pythonw: use the console python
        py = py[:-len("pythonw.exe")] + "python.exe"
    return [py, "-m", "peakforge", "mcp"]


def config_snippets() -> dict:
    cmd = server_command()
    claude_cli = "claude mcp add peakforge -- " + " ".join(f'"{c}"' if " " in c else c for c in cmd)
    return {
        "claude_code_cli": claude_cli,
        "mcp_json": {"mcpServers": {"peakforge": {"command": cmd[0], "args": cmd[1:]}}},
        "codex_toml": f'[mcp_servers.peakforge]\ncommand = "{cmd[0]}"\nargs = {cmd[1:]!r}'.replace("'", '"'),
    }


AGENTS_MD = """<!-- PeakForge:BEGIN -->
## PeakForge XPS project

This folder is analysed with PeakForge. Drive it through the `peakforge` MCP server (tools: status,
add_files, charge_correct, list_presets, apply_preset, add_component, set_param, set_background,
fit, diagnostics, batch_apply, quantify, export, render) or the CLI (`peakforge --help`).

Rules
- Never modify `data/raw/` (read-only raw data). Results go to `output/`.
- Charge-correct first (C 1s C–C = 284.8 eV unless told otherwise) and state the shift used.
- Before reporting oxidation-state fractions run `diagnostics`; mention bound hits, strongly
  correlated parameters and components that ΔBIC says are not supported.
- Keep spin-orbit splitting / area ratios fixed to literature values unless the user asks.
- Label conclusions as measured / fitted / inferred.
- If no project exists yet, create one here (create_project) and import the data files of this folder.
- Remind the user to cross-check final numbers with CasaXPS / Avantage / MultiPak before publication.
<!-- PeakForge:END -->
"""


def connect_folder(folder: str) -> dict:
    """One-click agent setup for a working folder (no command line needed):
    writes/merges .mcp.json (project-scoped MCP server used by Claude Code / Claude desktop Code tab,
    Cursor, …) and AGENTS.md + CLAUDE.md with analysis rules. Returns the written paths."""
    import json
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, ".mcp.json")
    cfg = {}
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError):
            cfg = {}
    cmd = server_command()
    cfg.setdefault("mcpServers", {})["peakforge"] = {"command": cmd[0], "args": cmd[1:]}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    md = write_agents_md(folder)
    return dict(mcp_json=path, agents_md=md)


def write_agents_md(project_root: str) -> str:
    path = os.path.join(project_root, "AGENTS.md")
    text = ""
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        if "<!-- PeakForge:BEGIN -->" in text:
            a = text.index("<!-- PeakForge:BEGIN -->")
            b = text.index("<!-- PeakForge:END -->") + len("<!-- PeakForge:END -->")
            text = text[:a] + AGENTS_MD.strip() + text[b:]
        else:
            text = text.rstrip() + "\n\n" + AGENTS_MD
    else:
        text = AGENTS_MD
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    claude = os.path.join(project_root, "CLAUDE.md")
    if not os.path.exists(claude):
        with open(claude, "w", encoding="utf-8") as f:
            f.write("@AGENTS.md\n")
    return path
