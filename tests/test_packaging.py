"""Pieces the packaged app relies on: update check, frozen MCP command, selftest, packaging files."""
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent


def test_version_comparison_and_check(monkeypatch):
    from peakforge import update
    assert update._vtuple("v1.10.0") > update._vtuple("1.9.3")
    monkeypatch.setattr(update, "latest_release", lambda timeout=4.0: "99.0.0")
    assert update.check()["newer"] is True
    monkeypatch.setattr(update, "latest_release", lambda timeout=4.0: None)
    assert update.check()["newer"] is None              # offline: no claim either way


def test_update_never_touches_the_network_for_upgrade_when_frozen(monkeypatch):
    from peakforge import update
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    ok, msg = update.upgrade()
    assert not ok and update.RELEASES_PAGE in msg


def test_mcp_command_in_packaged_app(monkeypatch):
    from peakforge import agent
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", r"C:\Apps\PeakForge\PeakForge.exe")
    cmd = agent.server_command()
    assert cmd[0].endswith("peakforge-cli.exe") and cmd[1:] == ["mcp"]
    snip = agent.config_snippets()["mcp_json"]["mcpServers"]["peakforge"]
    assert snip["command"].endswith("peakforge-cli.exe") and snip["args"] == ["mcp"]


def test_selftest_passes_from_source():
    from peakforge import selftest
    assert selftest.run() == 0


def test_spec_bundles_origin_builder_and_package_data():
    spec = (ROOT / "packaging" / "peakforge.spec").read_text(encoding="utf-8")
    assert "origin_builder.py" in spec                  # copied next to exported data, so it must be a real file
    assert 'collect_all("peakforge")' in spec
    cfg = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "docs/*.md" in cfg and "docs/images/*.png" in cfg


def test_installer_script_matches_package():
    iss = (ROOT / "packaging" / "peakforge.iss").read_text(encoding="utf-8")
    assert "dist\\PeakForge" in iss and "examples" in iss and ".xpsproj" in iss
    assert (ROOT / "src" / "peakforge" / "assets" / "peakforge.ico").exists()
