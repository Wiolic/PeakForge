"""PeakForge command line.  `peakforge <command> --help` for details.

  peakforge gui [project]                 open the desktop app
  peakforge init <folder> [--name N]      create a project
  peakforge add <project> <files...>      import .vms/.spe/.csv/.xlsx (copied to data/raw, read-only)
  peakforge status <project>              samples, spectra, shifts, fit state (JSON)
  peakforge charge <project> [--ref 284.8] [--sample S] [--set VALUE]
  peakforge presets [--region "Ir 4f"]
  peakforge preset <project> <key> [<preset_id>]
  peakforge fit <project> [keys...] [--region R] [--sample S] [--starts 3] [--deep]
  peakforge param <project> <key> <Comp.param> [--value V] [--min] [--max] [--fix|--free] [--expr E]
  peakforge model <project> <key> [--set model.json]
  peakforge diagnose <project> <key>
  peakforge batch <project> <source_key> [--fix fwhm eta]
  peakforge quant <project>
  peakforge export <project> [--formats png xlsx origin] [--theme glacier] [--out DIR]
  peakforge mcp                           run the MCP server (stdio) for AI agents
  peakforge agent-config                  print MCP client configuration snippets
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__


def _print(o):
    sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
    print(json.dumps(o, ensure_ascii=False, indent=1, default=str))


def main(argv=None):
    ap = argparse.ArgumentParser(prog="peakforge", description="PeakForge — XPS analysis. Developed by Eggy & Claude Opus 5.5")
    ap.add_argument("--version", action="version", version=f"PeakForge {__version__}")
    sub = ap.add_subparsers(dest="cmd")

    g = sub.add_parser("gui"); g.add_argument("project", nargs="?")
    i = sub.add_parser("init"); i.add_argument("folder"); i.add_argument("--name")
    a = sub.add_parser("add"); a.add_argument("project"); a.add_argument("files", nargs="+")
    a.add_argument("--no-copy", action="store_true")
    a.add_argument("--template", help="column template saved in the project (tables)")
    v = sub.add_parser("validate", help="check project file, column templates, models and presets")
    v.add_argument("project")
    sub.add_parser("formats", help="list file formats (readers)")
    dg = sub.add_parser("diag", help="write a diagnostics bundle (logs, versions, project/model JSON; no raw data)")
    dg.add_argument("project", nargs="?"); dg.add_argument("--out")
    s = sub.add_parser("status"); s.add_argument("project")
    c = sub.add_parser("charge"); c.add_argument("project"); c.add_argument("--ref", type=float)
    c.add_argument("--sample"); c.add_argument("--set", type=float, dest="value")
    pr = sub.add_parser("presets"); pr.add_argument("--region"); pr.add_argument("--project")
    ap_ = sub.add_parser("preset"); ap_.add_argument("project"); ap_.add_argument("key"); ap_.add_argument("preset_id", nargs="?")
    f = sub.add_parser("fit"); f.add_argument("project"); f.add_argument("keys", nargs="*")
    f.add_argument("--region"); f.add_argument("--sample"); f.add_argument("--starts", type=int, default=3)
    f.add_argument("--deep", action="store_true")
    pa = sub.add_parser("param"); pa.add_argument("project"); pa.add_argument("key"); pa.add_argument("param")
    pa.add_argument("--value", type=float); pa.add_argument("--min", type=float); pa.add_argument("--max", type=float)
    pa.add_argument("--fix", action="store_true"); pa.add_argument("--free", action="store_true"); pa.add_argument("--expr")
    mo = sub.add_parser("model"); mo.add_argument("project"); mo.add_argument("key"); mo.add_argument("--set", dest="setfile")
    d = sub.add_parser("diagnose"); d.add_argument("project"); d.add_argument("key")
    b = sub.add_parser("batch"); b.add_argument("project"); b.add_argument("source")
    b.add_argument("--fix", nargs="*", default=["fwhm"]); b.add_argument("--targets", nargs="*")
    q = sub.add_parser("quant"); q.add_argument("project")
    e = sub.add_parser("export"); e.add_argument("project"); e.add_argument("--formats", nargs="*", default=["png", "xlsx", "origin"])
    e.add_argument("--theme"); e.add_argument("--out")
    sub.add_parser("mcp")
    sub.add_parser("agent-config")

    args = ap.parse_args(argv)
    if args.cmd in (None, "gui"):
        from .gui.app import run
        return run(getattr(args, "project", None))
    if args.cmd == "mcp":
        from .mcp_server import main as mcp_main
        return mcp_main()
    if args.cmd == "agent-config":
        from .agent import config_snippets
        _print(config_snippets())
        return 0

    from . import ops
    from .project import Project
    if args.cmd == "init":
        p = Project.create(args.folder, args.name)
        _print(dict(project=p.path))
        return 0
    if args.cmd == "formats":
        from .io import list_formats
        _print(list_formats())
        return 0
    if args.cmd == "validate":
        from . import schema
        rep = schema.validate_project(args.project)
        sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, "reconfigure") else None
        print(rep.text())
        print(f"{rep.n_err} error(s), {rep.n_warn} warning(s)")
        return 1 if rep.n_err else 0
    if args.cmd == "diag":
        from . import logs
        p = Project.open(args.project) if args.project else None
        _print(dict(diagnostics=str(logs.diagnostics_zip(args.out, p))))
        return 0
    if args.cmd == "presets":
        p = Project.open(args.project) if args.project else None
        _print(ops.list_presets(p, args.region))
        return 0
    p = Project.open(args.project)
    if args.cmd == "add":
        _print({fn: p.add_file(fn, copy=not args.no_copy, template=args.template) for fn in args.files})
    elif args.cmd == "status":
        _print(ops.status(p))
    elif args.cmd == "charge":
        if args.value is not None:
            if not args.sample:
                ap.error("--set needs --sample")
            p.set_shift(args.sample, args.value)
            _print({args.sample: args.value})
        else:
            _print(p.auto_charge(args.sample, args.ref))
    elif args.cmd == "preset":
        _print(ops.apply_preset(p, args.key, args.preset_id))
    elif args.cmd == "fit":
        _print(ops.fit(p, args.keys or None, args.region, args.sample, args.starts, args.deep))
    elif args.cmd == "param":
        vary = True if args.free else (False if args.fix else None)
        _print(ops.set_param(p, args.key, args.param, args.value, args.min, args.max, vary, args.expr))
    elif args.cmd == "model":
        if args.setfile:
            with open(args.setfile, encoding="utf-8") as fh:
                _print(ops.set_model(p, args.key, json.load(fh)))
        else:
            _print(ops.model_json(p, args.key))
    elif args.cmd == "diagnose":
        _print(ops.diagnostics(p, args.key))
    elif args.cmd == "batch":
        _print(ops.batch(p, args.source, targets=args.targets, fix=args.fix))
    elif args.cmd == "quant":
        _print(p.quantify())
    elif args.cmd == "export":
        from .export.exporter import export_all
        _print(export_all(p, out_dir=args.out, theme=args.theme, formats=tuple(args.formats)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
