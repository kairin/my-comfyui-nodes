"""CLI module for the comfygo model registry.

Provides model listing, filtering, and reconcile subcommands.
Called by the ``comfygo-models.sh`` shell wrapper.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

from . import reconciler
from . import scanner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comfygo models",
        description="Inspect and reconcile the ComfyUI model library.",
    )
    parser.add_argument(
        "-f",
        "--filter",
        dest="filter",
        type=str,
        default=None,
        help="Case-insensitive substring filter for model names",
    )
    parser.add_argument(
        "--models-dir",
        type=str,
        default=None,
        help="Override the model root directory (default: folder_paths.models_dir)",
    )
    sub = parser.add_subparsers(dest="command")

    reconcile_parser = sub.add_parser("reconcile", help="Reconcile compatibility views")
    reconcile_parser.add_argument(
        "-f",
        "--filter",
        dest="reconcile_filter",
        type=str,
        default=None,
        help="Case-insensitive substring filter for model names",
    )
    reconcile_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Apply changes (default is dry-run)",
    )

    gc_parser = sub.add_parser("gc", help="Report or quarantine managed model folders")
    gc_parser.add_argument(
        "-f",
        "--filter",
        dest="gc_filter",
        type=str,
        default=None,
        help="Case-insensitive substring filter for folder names",
    )
    gc_parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Quarantine the matching managed folder (requires -f NAME)",
    )

    return parser


def get_models_dir(override: str | None = None) -> pathlib.Path:
    """Resolve the models directory to a canonical absolute path."""
    if override is not None:
        return pathlib.Path(override).resolve()
    try:
        import folder_paths  # type: ignore[import-untyped]

        raw = getattr(folder_paths, "models_dir", None)
        if not raw:
            print(
                "Error: folder_paths.models_dir is not set.",
                file=sys.stderr,
            )
            sys.exit(1)
        return pathlib.Path(str(raw)).resolve()
    except ImportError:
        print(
            "Error: folder_paths not available. "
            "Use --models-dir to specify explicitly.",
            file=sys.stderr,
        )
        sys.exit(1)


def cmd_list(
    packages: list,
    *,
    models_dir: pathlib.Path | None = None,
    filter_str: str | None = None,
) -> None:
    """List models with optional filter."""
    identified = [p for p in packages if not p.ambiguous]
    ambiguous = [p for p in packages if p.ambiguous]

    if filter_str:
        filtered = [p for p in identified if filter_str.lower() in p.name.lower()]
        if not filtered:
            print(f"No models matching '{filter_str}'")
            return
        for pkg in filtered:
            print(f"{pkg.name}  canonical: {pkg.path}")
            for comp in pkg.components:
                cats = ", ".join(comp.comfy_categories)
                comp_path = comp.resolved_path(pkg.path)
                print(f"  {comp.logical_name} → {cats}  ({comp_path})")
        return

    # Summary mode: show each root seen.
    roots: set[pathlib.Path] = set()
    for p in packages:
        r = p.path.parent
        if r.exists():
            roots.add(r)

    if len(roots) == 1:
        root_str = str(next(iter(roots)))
    elif roots:
        root_str = ", ".join(str(r) for r in sorted(roots))
    elif models_dir is not None:
        root_str = str(models_dir)
    else:
        root_str = "?"

    print(f"Model root(s): {root_str}")
    print(f"Identified packages: {len(identified)}")
    print(f"Ambiguous folders: {len(ambiguous)}")


def cmd_reconcile(
    packages: list,
    models_dir: pathlib.Path,
    filter_str: str | None = None,
    apply: bool = False,
) -> None:
    """Run reconcile with optional filter."""
    target = packages
    if filter_str:
        target = [
            p
            for p in packages
            if not p.ambiguous and filter_str.lower() in p.name.lower()
        ]
        if not target:
            print(f"No identifiable packages matching '{filter_str}'")
            return

    if not apply:
        print("Dry-run reconcile:")
    report = reconciler.reconcile(target, models_dir, dry_run=not apply)

    if not apply:
        report.print_report(prefix="  ")
        print()
        print(report.summary)
        print("Use --apply to apply changes.")
    else:
        report.print_report(prefix="  ")
        print()
        print(f"Reconcile complete: {report.summary}")


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    models_dir = get_models_dir(args.models_dir)

    if args.command == "gc":
        from . import gc

        # Gate: --apply requires -f NAME (no bulk quarantine).
        gc_filter: str | None = getattr(args, "gc_filter", None) or args.filter
        if args.apply and not gc_filter:
            print("error: --apply requires -f NAME", file=sys.stderr)
            sys.exit(1)

        report = gc.run_gc(models_dir, filter_str=gc_filter, apply=args.apply)
        if report.errors:
            sys.exit(1)
        return

    legacy_roots: list[pathlib.Path] = []
    for legacy_sub in ("diffusers", "library"):
        legacy_path = models_dir / legacy_sub
        if legacy_path.is_dir():
            legacy_roots.append(legacy_path)

    packages = scanner.scan_models(models_dir, extra_roots=legacy_roots)

    if args.command == "reconcile":
        # The reconcile subparser stores its --filter on a separate dest
        # so either global or subcommand filter placement works.
        filter_val = getattr(args, "reconcile_filter", None) or args.filter
        cmd_reconcile(packages, models_dir, filter_str=filter_val, apply=args.apply)
    else:
        cmd_list(packages, models_dir=models_dir, filter_str=args.filter)


if __name__ == "__main__":
    main()
