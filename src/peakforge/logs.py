"""Logging and the diagnostics bundle (adapted from XAFSmith).

- Log file: ~/.peakforge/peakforge.log (rotating, 3 × 1 MB), shared by GUI, CLI and MCP server.
- ``log`` is the package logger; ``except`` blocks that swallow an error call ``log.warning`` /
  ``log.exception`` instead of passing silently. PEAKFORGE_DEBUG=1 also records debug messages.
- ``install_excepthook()`` writes uncaught exceptions to the log (the GUI also shows them).
- ``diagnostics_zip()`` bundles the log, versions/environment, the project file, model JSON and a
  validation report — **never raw spectra** (data/raw is not included) — to send to the developer.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import platform
import sys
import traceback
import zipfile
from datetime import datetime
from pathlib import Path

LOG_DIR = Path(os.path.expanduser("~")) / ".peakforge"
LOG_FILE = LOG_DIR / "peakforge.log"

log = logging.getLogger("peakforge")
_configured = False


def setup(level: int | None = None) -> logging.Logger:
    """Configure the rotating file log once. If the file cannot be written, logs are dropped."""
    global _configured
    if _configured:
        return log
    _configured = True
    level = level or (logging.DEBUG if os.environ.get("PEAKFORGE_DEBUG") else logging.INFO)
    log.setLevel(level)
    try:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3, encoding="utf-8")
        h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        log.addHandler(h)
    except OSError:
        log.addHandler(logging.NullHandler())
    log.propagate = False       # never print to stdout (the MCP server speaks JSON-RPC there)
    return log


def format_exc(exc_info=None) -> str:
    et, ev, tb = exc_info or sys.exc_info()
    return "".join(traceback.format_exception(et, ev, tb))


def install_excepthook(on_error=None):
    """Uncaught exception → log; on_error(text) lets the GUI show it."""
    setup()
    old = sys.excepthook

    def hook(et, ev, tb):
        text = "".join(traceback.format_exception(et, ev, tb))
        log.error("uncaught exception\n%s", text)
        if on_error:
            try:
                on_error(text)
            except Exception:       # noqa: BLE001 — the error box itself failed
                log.exception("error dialog failed")
        if old is not sys.__excepthook__:
            old(et, ev, tb)
        elif not on_error:
            sys.__excepthook__(et, ev, tb)
    sys.excepthook = hook


def environment_info() -> dict:
    from . import __version__
    info = {"peakforge": __version__, "python": sys.version.split()[0], "platform": platform.platform(),
            "executable": sys.executable, "frozen": bool(getattr(sys, "frozen", False)),
            "encoding": sys.getfilesystemencoding(), "preferred_encoding": _preferred_encoding(),
            "time": datetime.now().isoformat(timespec="seconds")}
    for mod in ("numpy", "scipy", "pandas", "matplotlib", "PySide6", "openpyxl", "mcp", "originpro"):
        try:
            m = __import__(mod)
            info[mod] = getattr(m, "__version__", "?")
        except Exception:           # noqa: BLE001 — any import failure means "not available"
            info[mod] = "not installed"
    return info


def _preferred_encoding() -> str:
    import locale
    return locale.getpreferredencoding(False)


def diagnostics_zip(dest: str | os.PathLike | None = None, project=None) -> Path:
    """Write the diagnostics bundle and return its path. ``project``: an open Project (optional)."""
    dest = Path(dest or (LOG_DIR / f"peakforge_diag_{datetime.now():%Y%m%d_%H%M%S}.zip"))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("environment.json", json.dumps(environment_info(), ensure_ascii=False, indent=1))
        for f in sorted(LOG_DIR.glob("peakforge.log*")):
            z.write(f, f"logs/{f.name}")
        settings = LOG_DIR / "settings.json"
        if settings.exists():
            z.write(settings, "settings.json")
        if project is not None:
            z.write(project.path, f"project/{os.path.basename(project.path)}")
            mdir = Path(project.root) / "models"
            for f in sorted(mdir.glob("*.json")):         # parameters and fit summaries, no spectra
                z.write(f, f"project/models/{f.name}")
            pdir = Path(project.root) / "presets"
            for f in sorted(pdir.glob("*.json")):
                z.write(f, f"project/presets/{f.name}")
            try:
                from . import schema
                z.writestr("validate.txt", schema.validate_project(project.path).text())
            except Exception:       # noqa: BLE001 — the bundle must still be written
                z.writestr("validate.txt", "validation failed:\n" + format_exc())
    log.info("diagnostics bundle written: %s", dest)
    return dest


setup()          # configure on import so warnings never reach the console
