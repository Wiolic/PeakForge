"""Windowed entry (PeakForge.exe, no console): always opens the GUI; a .xpsproj argument opens that project."""
import multiprocessing
import sys

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from peakforge import cli
    if len(sys.argv) == 1:
        sys.argv.append("gui")
    elif sys.argv[1].lower().endswith(".xpsproj"):
        sys.argv.insert(1, "gui")
    cli.main()
