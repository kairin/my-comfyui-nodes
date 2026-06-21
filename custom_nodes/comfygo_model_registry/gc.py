"""Garbage collection for model folders owned by comfygo.

Marker presence only means "comfygo has seen this folder".
It does NOT mean the folder is eligible for automatic removal.
Only explicit -f NAME --apply triggers quarantine.
"""

from __future__ import annotations

import dataclasses
import errno
import json
import os
import pathlib
from datetime import date
from typing import Optional

from . import models
from . import scanner


@dataclasses.dataclass
class Marker:
    """An ownership proof file discovered during GC scan."""

    type: str  # "downloader" or "descriptor"
    path: pathlib.Path
    parseable: bool


@dataclasses.dataclass
class ManagedFolder:
    """A folder with at least one marker file.

    Managed means "comfygo knows this folder" -- not "garbage."
    Only -f NAME --apply triggers quarantine.
    """

    name: str
    path: pathlib.Path
    markers: list[Marker]


@dataclasses.dataclass
class AmbiguousFolder:
    """A folder with no marker file. GC reports but never moves."""

    name: str
    path: pathlib.Path
    reason: str = "no marker file found"


@dataclasses.dataclass
class SkippedFolder:
    """A folder or entry skipped during scan for safety/scope reasons."""

    name: str
    path: pathlib.Path
    reason: str  # "reserved folder", "hidden folder", "source symlink", etc.


@dataclasses.dataclass
class QuarantineOperation:
    """A single quarantine attempt performed during apply mode."""

    source: pathlib.Path
    destination: pathlib.Path
    status: str  # "completed", "skipped", or "failed"
    reason: str = ""


@dataclasses.dataclass
class GCReport:
    """The output of a full GC pass -- dry-run or apply."""

    managed: list[ManagedFolder] = dataclasses.field(default_factory=list)
    ambiguous: list[AmbiguousFolder] = dataclasses.field(default_factory=list)
    skipped: list[SkippedFolder] = dataclasses.field(default_factory=list)
    operations: list[QuarantineOperation] = dataclasses.field(default_factory=list)
    warnings: list[str] = dataclasses.field(default_factory=list)
    errors: list[str] = dataclasses.field(default_factory=list)
    apply_requested: bool = False
    apply_filter: Optional[str] = None
    selected_target: Optional[ManagedFolder] = None
    quarantined: Optional[str] = None  # destination path of quarantined folder


# Reserved ComfyUI category folder names that GC must skip. GC reuses the
# scanner policy for names only; it does not delegate discovery to scanner.
_RESERVED_NAMES: frozenset[str] = frozenset(scanner._RESERVED_CATEGORY_FOLDERS)


def _source_symlink_warning(path: pathlib.Path) -> str:
    return f"warning: Refusing to quarantine symlinked folder '{path}'"


def detect_markers(folder: pathlib.Path) -> list[Marker]:
    """Check a folder for ownership marker files."""
    markers: list[Marker] = []

    download_marker = folder / ".comfygo-download.json"
    if download_marker.is_file():
        parseable = False
        try:
            json.loads(download_marker.read_text())
            parseable = True
        except (json.JSONDecodeError, OSError):
            pass
        markers.append(
            Marker(
                type="downloader",
                path=download_marker,
                parseable=parseable,
            )
        )

    descriptor_marker = folder / "comfygo-model.json"
    if descriptor_marker.is_file():
        parseable = False
        try:
            json.loads(descriptor_marker.read_text())
            parseable = True
        except (json.JSONDecodeError, OSError):
            pass
        markers.append(
            Marker(
                type="descriptor",
                path=descriptor_marker,
                parseable=parseable,
            )
        )

    return markers


def is_hidden(name: str) -> bool:
    """Dot-prefixed names are hidden."""
    return name.startswith(".")


def scan_model_root(models_dir: pathlib.Path) -> GCReport:
    """Scan top-level model root directories for GC classification.

    v1: Top-level only -- no legacy extra_roots, no recursion.
    """
    report = GCReport()

    entries = sorted(models_dir.iterdir(), key=lambda e: e.name.lower())
    for entry in entries:
        name = entry.name

        if is_hidden(name):
            report.skipped.append(
                SkippedFolder(name=name, path=entry, reason="hidden folder")
            )
            continue

        if name.lower() in _RESERVED_NAMES:
            report.skipped.append(
                SkippedFolder(name=name, path=entry, reason="reserved folder")
            )
            continue

        if entry.is_symlink():
            report.skipped.append(
                SkippedFolder(name=name, path=entry, reason="source symlink")
            )
            report.warnings.append(_source_symlink_warning(entry))
            continue

        if not entry.is_dir():
            report.skipped.append(
                SkippedFolder(name=name, path=entry, reason="non-directory")
            )
            continue

        markers = detect_markers(entry)
        if markers:
            report.managed.append(ManagedFolder(name=name, path=entry, markers=markers))
            for m in markers:
                if not m.parseable:
                    report.warnings.append(
                        f"{name}: unparseable {m.type} marker ({m.path})"
                    )
        else:
            report.ambiguous.append(AmbiguousFolder(name=name, path=entry))

    return report


def _filter_report(
    report: GCReport, filter_str: str | None
) -> tuple[list[ManagedFolder], list[AmbiguousFolder]]:
    """Apply case-insensitive substring filter to report lists."""
    if not filter_str:
        return report.managed, report.ambiguous
    flt = filter_str.lower()
    managed = [m for m in report.managed if flt in m.name.lower()]
    ambiguous = [a for a in report.ambiguous if flt in a.name.lower()]
    return managed, ambiguous


def _filter_warnings(report: GCReport, filter_str: str | None) -> list[str]:
    """Apply the report filter to warning entries."""
    if not filter_str:
        return report.warnings
    flt = filter_str.lower()
    return [w for w in report.warnings if flt in w.lower()]


def _source_symlink_warnings(
    report: GCReport,
    filter_str: str | None,
) -> list[str]:
    """Return source-symlink warnings, optionally filtered by entry name."""
    warnings: list[str] = []
    flt = filter_str.lower() if filter_str else None
    for skipped in report.skipped:
        if skipped.reason != "source symlink":
            continue
        if flt and flt not in skipped.name.lower():
            continue
        warnings.append(_source_symlink_warning(skipped.path))
    return warnings


def print_report(report: GCReport, filter_str: str | None = None) -> None:
    """Print a human-readable GC dry-run report."""
    managed, ambiguous = _filter_report(report, filter_str)
    warnings = _filter_warnings(report, filter_str)

    if not managed and not ambiguous and not warnings:
        print("Nothing to report.")
        return

    if managed:
        print("Managed folders:")
        for mf in managed:
            marker_types = ", ".join(m.type for m in mf.markers)
            print(f"  {mf.path}")
            print(f"    marker: {marker_types}")
        print()

    if ambiguous:
        print("Ambiguous:")
        for af in ambiguous:
            print(f"  {af.path}")
            print(f"    {af.reason}")
        print()

    if warnings:
        print("Warnings:")
        for w in warnings:
            print(f"  {w}")
        print()


# ── Quarantine safety helpers ──────────────────────────────────────


def _validate_trash_safety(trash_root: pathlib.Path) -> None:
    """Raise error if .comfygo_trash is a symlink."""
    if trash_root.is_symlink():
        raise OSError(errno.EINVAL, "Refusing to operate: .comfygo_trash is a symlink")


def _resolve_destination(
    trash_root: pathlib.Path,
    model_name: str,
    today: date | None = None,
) -> tuple[pathlib.Path, str | None]:
    """Compute collision-free destination under .comfygo_trash/<date>/<name>/.

    If the destination already exists (directory, file, or symlink),
    append -1, -2, etc. Never overwrites.
    """
    today = today or date.today()
    dated = trash_root / today.isoformat() / model_name
    candidate = dated
    collision = False

    # Validate path segments
    models.validate_path_segment(today.isoformat())
    models.validate_path_segment(model_name)

    suffix = 0
    while True:
        # Symlink at destination is a collision
        if candidate.is_symlink() or candidate.exists():
            collision = True
            suffix += 1
            candidate = dated.with_name(f"{model_name}-{suffix}")
        else:
            break
        if suffix > 100:
            raise RuntimeError(
                f"Too many collisions for {model_name} under {dated.parent}"
            )
    warning = None
    if collision:
        warning = f"warning: Destination already exists; using '{candidate}'"
    return candidate, warning


def quarantine(
    folder: ManagedFolder,
    models_dir: pathlib.Path,
    today: date | None = None,
) -> QuarantineOperation:
    """Move a managed folder to .comfygo_trash/<date>/<name>/ via os.rename().

    Raises OSError on cross-filesystem (EXDEV) or permission errors.
    No copy+delete fallback.
    """
    today = today or date.today()
    root = models_dir.resolve()
    trash_root = root / ".comfygo_trash"

    # Safety checks
    folder_path = folder.path

    # Source must be a direct top-level entry under model root.
    if folder_path.parent.resolve() != root:
        raise OSError(
            errno.EINVAL, f"Source folder {folder_path} is not a direct child of {root}"
        )

    if folder_path.is_symlink():
        raise OSError(
            errno.EINVAL, f"Refusing to quarantine symlinked folder '{folder_path}'"
        )

    if not folder_path.is_dir():
        raise OSError(errno.ENOENT, f"Source folder does not exist: {folder_path}")

    # Trash root safety
    if trash_root.exists():
        _validate_trash_safety(trash_root)

    # Resolve destination with collision handling
    destination, warning = _resolve_destination(trash_root, folder.name, today)

    # Create trash + date directories
    destination.parent.mkdir(parents=True, exist_ok=True)

    # Date directory safety (must not be a symlink after creation)
    if destination.parent.is_symlink():
        raise OSError(
            errno.EINVAL, f"Trash date directory is a symlink: {destination.parent}"
        )

    # Perform the rename.
    # T044: os.rename() is the ONLY mutating call in the entire GC apply
    # path.  No shutil, no copytree, no remove, no copy+delete fallback.
    os.rename(str(folder_path), str(destination))
    return QuarantineOperation(
        source=folder_path,
        destination=destination,
        status="completed",
        reason=warning or "",
    )


def run_gc(
    models_dir: pathlib.Path,
    filter_str: str | None = None,
    apply: bool = False,
) -> GCReport:
    """Entry point for the gc CLI subcommand.

    Dry-run (default): scan and print report.
    Apply: requires -f NAME; quarantine exactly one managed folder.

    T050: GC v1 never walks, prunes, or maintains .comfygo_trash contents.
    The only mutations are: creating the dated trash directory and
    performing a single os.rename() of the selected folder.
    """
    report = scan_model_root(models_dir)
    report.apply_requested = apply
    report.apply_filter = filter_str

    if not apply:
        if filter_str:
            managed, ambiguous = _filter_report(report, filter_str)
            symlink_warnings = _source_symlink_warnings(report, filter_str)
            warnings = _filter_warnings(report, filter_str)
            if not managed and not ambiguous and symlink_warnings:
                report.errors.extend(symlink_warnings)
                for warning in symlink_warnings:
                    print(warning)
                return report
            if not managed and not ambiguous and not warnings:
                msg = f"No folders matching '{filter_str}'"
                report.errors.append(msg)
                print(f"error: {msg}")
                return report

        print_report(report, filter_str=filter_str)
        return report

    # Apply mode: requires -f NAME
    if not filter_str:
        report.errors.append("--apply requires -f NAME")
        print("error: --apply requires -f NAME")
        return report

    flt = filter_str.lower()
    managed_matches = [m for m in report.managed if flt in m.name.lower()]
    ambiguous_matches = [a for a in report.ambiguous if flt in a.name.lower()]
    symlink_warnings = _source_symlink_warnings(report, filter_str)

    # No managed match
    if not managed_matches:
        if symlink_warnings and not ambiguous_matches:
            report.errors.extend(symlink_warnings)
            for warning in symlink_warnings:
                print(warning)
        elif ambiguous_matches:
            msg = f"Folder '{filter_str}' is not managed by comfygo"
            report.errors.append(msg)
            print(f"error: {msg}")
        else:
            msg = f"No managed folder matching '{filter_str}'"
            report.errors.append(msg)
            print(f"error: {msg}")
        return report

    # Multiple managed matches
    if len(managed_matches) > 1:
        msg = f"Filter '{filter_str}' matched multiple managed folders"
        report.errors.append(msg)
        print(f"error: {msg}")
        for mf in managed_matches:
            print(f"  {mf.path}")
        return report

    # Exactly one managed match
    target = managed_matches[0]
    report.selected_target = target
    try:
        operation = quarantine(target, models_dir)
        report.operations.append(operation)
        report.quarantined = str(operation.destination)
        if operation.reason:
            report.warnings.append(operation.reason)
            print(operation.reason)
        print("Quarantined:")
        print(f"  {target.path}")
        print(f"    -> {operation.destination}")
    except ValueError as exc:
        msg = f"{exc}; no files changed"
        report.errors.append(msg)
        report.operations.append(
            QuarantineOperation(
                source=target.path,
                destination=pathlib.Path(),
                status="failed",
                reason=msg,
            )
        )
        print(f"error: {msg}")
    except OSError as exc:
        if exc.errno == errno.EXDEV:
            msg = "Cannot quarantine across filesystems; no files changed"
        elif exc.errno in (errno.EACCES, errno.EPERM):
            msg = f"Permission denied: {target.path}; no files changed"
        else:
            msg = str(exc)
        report.errors.append(msg)
        report.operations.append(
            QuarantineOperation(
                source=target.path,
                destination=pathlib.Path(),
                status="failed",
                reason=msg,
            )
        )
        print(f"error: {msg}")

    return report
