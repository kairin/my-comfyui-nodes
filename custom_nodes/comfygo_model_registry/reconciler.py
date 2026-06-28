"""Reconciler: symlink generation, pruning, conflict handling.

Supports dry-run and apply modes. Idempotent — re-running apply produces
identical state.
"""

from __future__ import annotations

import pathlib
from typing import Optional

from . import compat_views
from . import models


class ReconcileReport:
    """Report of what a reconcile pass would do or has done."""

    def __init__(self) -> None:
        self.views_created: list[pathlib.Path] = []
        self.views_pruned: int = 0
        self.conflicts: list[str] = []
        self.warnings: list[str] = []

    @property
    def summary(self) -> str:
        parts = []
        if self.views_created:
            parts.append(f"{len(self.views_created)} view(s) created")
        if self.views_pruned:
            parts.append(f"{self.views_pruned} stale view(s) pruned")
        if self.conflicts:
            parts.append(f"{len(self.conflicts)} conflict(s) detected")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warning(s)")
        if not parts:
            return "Nothing to do — all views are up to date."
        return "; ".join(parts)

    def print_report(self, prefix: str = "") -> None:
        for c in self.conflicts:
            print(f"{prefix}Conflict: {c}")
        for w in self.warnings:
            print(f"{prefix}Warning: {w}")
        for v in self.views_created:
            print(f"{prefix}Created: {v}")
        if self.views_pruned:
            print(f"{prefix}Pruned {self.views_pruned} stale view(s)")


def _view_component_name(comp: models.Component, target_path: pathlib.Path) -> str:
    """Use the weight filename for file components so ComfyUI extension filters match."""
    if target_path.is_file():
        return target_path.name
    return comp.logical_name


def reconcile(
    packages: list[models.ModelPackage],
    models_dir: pathlib.Path,
    dry_run: bool = True,
) -> ReconcileReport:
    """Reconcile compatibility views for identified model packages.

    In dry-run mode (default), reports what would be created/removed without
    modifying the filesystem. In apply mode, creates symlinks and prunes stale
    entries.

    Returns a ReconcileReport with the results.
    """
    report = ReconcileReport()
    models_dir = models_dir.resolve()

    if compat_views.views_root_is_symlink(models_dir):
        report.warnings.append(
            f"{compat_views.views_root(models_dir)} is a symlink — "
            "skipping all compatibility view operations"
        )
        return report

    # Build the set of views that should exist.
    desired_views: set[models.CompatibilityView] = set()
    for pkg in packages:
        if pkg.ambiguous:
            report.warnings.append(
                f"Skipping ambiguous package '{pkg.name}' — "
                f"no descriptor or inference match"
            )
            continue
        for comp in pkg.components:
            if not comp.exists(pkg.path):
                report.warnings.append(
                    f"Package '{pkg.name}': component '{comp.logical_name}' "
                    f"path does not exist — skipping"
                )
                continue
            target_path = comp.resolved_path(pkg.path)
            if not _path_within(target_path, pkg.path) or not _path_within(
                target_path, models_dir
            ):
                report.warnings.append(
                    f"Package '{pkg.name}': component '{comp.logical_name}' "
                    f"resolves outside the package or model root — skipping"
                )
                continue
            view_name = _view_component_name(comp, target_path)
            for category in comp.comfy_categories:
                view = models.CompatibilityView(
                    category=category,
                    model_name=pkg.name,
                    component_name=view_name,
                    target_path=target_path,
                )

                # Check for conflicts with already-registered views.
                conflict_key = f"{category}/{pkg.name}/{view_name}"
                existing = _find_matching_view(
                    desired_views, category, pkg.name, view_name
                )
                if existing is not None:
                    report.conflicts.append(
                        f"{conflict_key}: "
                        f"'{existing.target_path}' already registered, "
                        f"skipping '{view.target_path}'"
                    )
                    continue

                desired_views.add(view)

    if dry_run:
        # Dry-run: report without modifying.
        _report_dry_run(models_dir, desired_views, report)
    else:
        # Apply mode: create symlinks and prune stale.
        _apply_reconcile(models_dir, desired_views, report)

    return report


def _path_within(child: pathlib.Path, parent: pathlib.Path) -> bool:
    """Return True when child resolves inside parent."""
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except (OSError, RuntimeError, ValueError):
        return False


def _find_matching_view(
    views: set[models.CompatibilityView],
    category: str,
    model_name: str,
    component_name: str,
) -> Optional[models.CompatibilityView]:
    """Find a view with matching category/model_name/component_name."""
    for v in views:
        if (
            v.category == category
            and v.model_name == model_name
            and v.component_name == component_name
        ):
            return v
    return None


def _report_dry_run(
    models_dir: pathlib.Path,
    desired_views: set[models.CompatibilityView],
    report: ReconcileReport,
) -> None:
    """Report what would be created and pruned in dry-run mode."""
    vroot = compat_views.views_root(models_dir)

    for v in desired_views:
        link = compat_views.view_path_for(
            models_dir, v.category, v.model_name, v.component_name
        )
        if link.is_symlink() or link.exists():
            existing_target = link.resolve()
            if existing_target == v.target_path.resolve():
                continue  # Already correct.
            report.conflicts.append(
                f"{link}: current target '{existing_target}' "
                f"would be replaced with '{v.target_path}'"
            )
        else:
            report.views_created.append(link)

    # Check for stale entries.
    if vroot.is_dir():
        current_paths = {
            compat_views.view_path_for(
                models_dir, v.category, v.model_name, v.component_name
            )
            for v in desired_views
        }
        for category_dir in vroot.iterdir():
            if category_dir.is_symlink():
                report.warnings.append(
                    f"Skipping symlinked view category during dry-run prune: "
                    f"{category_dir}"
                )
                continue
            if not category_dir.is_dir():
                continue
            for model_dir in category_dir.iterdir():
                if model_dir.is_symlink():
                    report.warnings.append(
                        f"Skipping symlinked view model dir during dry-run "
                        f"prune: {model_dir}"
                    )
                    continue
                if not model_dir.is_dir():
                    continue
                for entry in model_dir.iterdir():
                    if entry in current_paths:
                        continue
                    if entry.is_symlink() or entry.is_file():
                        report.views_pruned += 1


def _apply_reconcile(
    models_dir: pathlib.Path,
    desired_views: set[models.CompatibilityView],
    report: ReconcileReport,
) -> None:
    """Apply the reconcile: create symlinks and prune stale."""
    # Create views.
    for v in desired_views:
        result = compat_views.create_view(models_dir, v)
        if result is not None:
            report.views_created.append(result)

    # Prune stale views.
    pruned = compat_views.remove_stale_views(models_dir, desired_views)
    report.views_pruned = pruned
