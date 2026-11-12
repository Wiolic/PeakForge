"""Update check: compare the installed version with the latest GitHub Release.

Only github.com is contacted, nothing about the user or the data is sent (4 s timeout; offline = quiet failure).
The packaged app cannot update itself: the user is pointed to the Releases page. A pip install can be upgraded
from the repository archive; a development install (pip install -e) is told to use git pull.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

from . import __version__
from .logs import log

REPO = "Wiolic/PeakForge"
RELEASE_API = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"
ZIP_URL = f"https://github.com/{REPO}/archive/refs/heads/main.zip"


def is_frozen() -> bool:
    """True in the packaged (PyInstaller) application."""
    return bool(getattr(sys, "frozen", False))


def _vtuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in re.findall(r"\d+", str(v))[:3]) or (0,)


def latest_release(timeout: float = 4.0) -> str | None:
    """Version of the newest GitHub Release (tag without the leading v); None if there is none or on failure."""
    try:
        req = urllib.request.Request(RELEASE_API, headers={"User-Agent": "PeakForge-update-check",
                                                           "Accept": "application/vnd.github+json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:   # noqa: S310 — fixed https URL
            tag = json.loads(r.read().decode("utf-8", "replace")).get("tag_name", "")
        return tag.lstrip("vV") or None
    except (OSError, ValueError):
        log.debug("update.latest_release failed", exc_info=True)
        return None


def is_editable() -> bool:
    if is_frozen():
        return False
    try:
        from importlib.metadata import distribution
        info = json.loads(distribution("peakforge").read_text("direct_url.json") or "{}")
        return bool(info.get("dir_info", {}).get("editable"))
    except Exception:       # noqa: BLE001 — metadata missing/odd: treat as not editable
        log.debug("update.is_editable failed", exc_info=True)
        return False


def check(timeout: float = 4.0) -> dict:
    """dict(current, latest, newer: bool | None (None = could not check), frozen, editable, page)."""
    lat = latest_release(timeout)
    return dict(current=__version__, latest=lat,
                newer=None if lat is None else _vtuple(lat) > _vtuple(__version__),
                frozen=is_frozen(), editable=is_editable(), page=RELEASES_PAGE)


def upgrade() -> tuple[bool, str]:
    """pip-install the newest source archive into the running environment; returns (ok, output tail)."""
    if is_frozen():
        return False, f"The packaged app cannot update itself: download the new installer from {RELEASES_PAGE}."
    if is_editable():
        return False, "Development install (pip install -e): run git pull in the source folder."
    py = Path(sys.executable)
    if py.name.lower() == "pythonw.exe" and (py.parent / "python.exe").exists():
        py = py.parent / "python.exe"
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    r = subprocess.run([str(py), "-m", "pip", "install", "--upgrade", ZIP_URL], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", creationflags=flags, check=False)
    return r.returncode == 0, (r.stdout or "")[-3000:] + (r.stderr or "")[-3000:]
