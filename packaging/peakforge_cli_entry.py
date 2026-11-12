"""Console entry (peakforge-cli.exe; Windows file names are case-insensitive, so it cannot be called PeakForge.exe):
command line and AI agents (`peakforge-cli.exe mcp`); same behaviour as the pip-installed `peakforge`."""
import multiprocessing

if __name__ == "__main__":
    multiprocessing.freeze_support()
    from peakforge import cli
    raise SystemExit(cli.main())
