""".comfygo_views directory management — create, prune, and clean symlink views."""

from __future__ import annotations

import pathlib
import shutil
from typing import Optional

from . import models

_VIEWS_DIR_NAME = ".comfygo_views"


def views_root(models_dir: pathlib.Path) -> pathlib.Path:
    """Return the path to the .comfygo_views directory under *models_dir*."""
    return models_dir / _VIEWS_DIR_NAME


def views_root_is_symlink(models_dir: pathlib.Path) -> bool:
    """Return True if the generated views root is itself a symlink."""
    return views_root(models_dir).is_symlink()


def view_path_for(
    models_dir: pathlib.Path,
    category: str,
    model_name: str,
    component_name: str,
) -> pathlib.Path:
    """Return the expected symlink path for a given component view.

    Validates all path segments to prevent traversal escapes.
    """
    models.validate_path_segment(category, context=" category")
    models.validate_path_segment(model_name, context=" model_name")
    models.validate_path_segment(component_name, context=" component_name")
    return views_root(models_dir) / category / model_name / component_name


def create_view(
    models_dir: pathlib.Path,
    view: models.CompatibilityView,
) -> Optional[pathlib.Path]:
    """Create a single compatibility symlink.

    Returns the symlink path on success, None if creation was skipped due to
    a conflict or missing target.
    """
    link = view_path_for(
        models_dir, view.category, view.model_name, view.component_name
    )
    target = view.target_path
    vroot = views_root(models_dir)
    category_dir = vroot / view.category
    model_dir = category_dir / view.model_name

    if vroot.is_symlink():
        print(f"Warning: skipping view operations because {vroot} is a symlink")
        return None
    if category_dir.is_symlink():
        print(
            f"Warning: skipping view for {view.model_name}/{view.component_name} "
            f"because category dir is a symlink: {category_dir}"
        )
        return None
    if model_dir.is_symlink():
        print(
            f"Warning: skipping view for {view.model_name}/{view.component_name} "
            f"because model dir is a symlink: {model_dir}"
        )
        return None

    if not target.exists():
        print(
            f"Warning: skipping view for {view.model_name}/{view.component_name} "
            f"— target does not exist: {target}"
        )
        return None

    link.parent.mkdir(parents=True, exist_ok=True)

    # Compute relative symlink from link → target using resolved paths
    # so that symlinked ancestors don't introduce .. escapes.
    rel_target = pathlib.Path(
        os_pathlib_relpath(str(target.resolve()), str(link.parent.resolve()))
    )

    if link.is_symlink() or link.exists():
        try:
            existing_target = link.resolve()
        except (OSError, RuntimeError):
            # Broken symlink — replace it.
            link.unlink(missing_ok=True)
        else:
            if existing_target == target.resolve():
                # Already points to the right place — idempotent.
                return None
            print(
                f"Warning: conflict at {link} — already points to "
                f"{existing_target}, skipping"
            )
            return None

    link.symlink_to(rel_target)
    return link


def remove_stale_views(
    models_dir: pathlib.Path,
    current_views: set[models.CompatibilityView],
) -> int:
    """Remove symlinks in .comfygo_views that are not in *current_views*.

    Returns the number of stale entries removed.
    """
    vroot = views_root(models_dir)
    if vroot.is_symlink():
        print(f"Warning: skipping stale view pruning because {vroot} is a symlink")
        return 0
    if not vroot.is_dir():
        return 0

    current_paths: set[pathlib.Path] = set()
    for v in current_views:
        current_paths.add(
            view_path_for(models_dir, v.category, v.model_name, v.component_name)
        )

    removed = 0
    for category_dir in vroot.iterdir():
        if category_dir.is_symlink():
            print(
                f"Warning: skipping symlinked view category during prune: "
                f"{category_dir}"
            )
            continue
        if not category_dir.is_dir():
            continue
        for model_dir in category_dir.iterdir():
            if model_dir.is_symlink():
                print(
                    f"Warning: skipping symlinked view model dir during prune: "
                    f"{model_dir}"
                )
                continue
            if not model_dir.is_dir():
                continue
            for entry in model_dir.iterdir():
                if entry in current_paths:
                    continue
                if entry.is_symlink() or entry.is_file():
                    entry.unlink()
                    removed += 1
            # Remove empty model directories.
            _remove_empty_dir(model_dir)
        _remove_empty_dir(category_dir)
    _remove_empty_dir(vroot)

    return removed


def clean_views(models_dir: pathlib.Path) -> None:
    """Remove the entire .comfygo_views directory."""
    vroot = views_root(models_dir)
    if vroot.is_symlink():
        print(f"Warning: refusing to clean symlinked views root: {vroot}")
        return
    if vroot.is_dir():
        shutil.rmtree(vroot)


def _remove_empty_dir(path: pathlib.Path) -> None:
    """Remove *path* if it is an empty directory."""
    try:
        if path.is_dir() and not path.is_symlink() and not any(path.iterdir()):
            path.rmdir()
    except OSError:
        pass


def os_pathlib_relpath(path: str, start: str) -> str:
    """Compute a relative path, working around pathlib/OS idiosyncrasies.

    Uses ``os.path.relpath`` internally and returns a string suitable for
    ``symlink_to``.
    """
    import os

    return os.path.relpath(path, start)
