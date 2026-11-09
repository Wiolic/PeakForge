"""Agent connection helpers: MCP client configuration snippets and project AGENTS.md."""
from __future__ import annotations

import os
import shutil
import sys


def server_command() -> list[str]:
    exe = shutil.which("peakforge")
    if exe:
        return [exe, "mcp"]
    return [sys.executable, "-m", "peakforge", "mcp"]


def config_snippets() -> dict:
    cmd = server_command()
    claude_cli = "claude mcp add peakforge -- " + " ".join(f'"{c}"' if " " in c else c for c in cmd)
    return {
        "claude_code_cli": claude_cli,
        "mcp_json": {"mcpServers": {"peakforge": {"command": cmd[0], "args": cmd[1:]}}},
        "codex_toml": f'[mcp_servers.peakforge]\ncommand = "{cmd[0]}"\nargs = {cmd[1:]!r}'.replace("'", '"'),
    }


AGENTS_MD = """<!-- PeakForge:BEGIN -->
## PeakForge (锻峰) XPS project

This folder is a PeakForge project. Drive it through the `peakforge` MCP server (tools: status,
add_files, charge_correct, list_presets, apply_preset, add_component, set_param, set_background,
fit, diagnostics, batch_apply, quantify, export, render) or the CLI (`peakforge --help`).

Rules
- Never modify `data/raw/` (read-only raw data). Results go to `output/`.
- Charge-correct first (C 1s C–C = 284.8 eV unless told otherwise) and state the shift used.
- Before reporting oxidation-state fractions run `diagnostics`; mention bound hits, strongly
  correlated parameters and components that ΔBIC says are not supported.
- Keep spin-orbit splitting / area ratios fixed to literature values unless the user asks.
- Label conclusions as measured / fitted / inferred.
<!-- PeakForge:END -->
"""


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
