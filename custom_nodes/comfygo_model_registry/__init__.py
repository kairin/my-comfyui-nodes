"""
comfygo_model_registry — ComfyUI custom node for descriptor-first model management.

At import time (ComfyUI startup), this module scans the configured model root,
reconciles compatibility views, and registers them with ComfyUI's folder_paths
system so existing node dropdowns see compatible model entries.
"""

from __future__ import annotations

import os
import pathlib

from . import compat_views
from . import reconciler
from . import scanner

# ComfyUI will import this module and call the mappings below.
NODE_CLASS_MAPPINGS: dict[str, type] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}


class ComfygoModelRegistry:
    """No-op utility node — the registry's value is in startup scan behavior."""

    OUTPUT_NODE = True

    @classmethod
    def INPUT_TYPES(cls) -> dict:
        return {
            "required": {},
        }

    RETURN_TYPES: tuple = ()
    FUNCTION = "noop"
    CATEGORY = "comfygo/utility"

    def noop(self) -> tuple:
        return ()


NODE_CLASS_MAPPINGS["ComfygoModelRegistry"] = ComfygoModelRegistry
NODE_DISPLAY_NAME_MAPPINGS["ComfygoModelRegistry"] = "Comfygo Model Registry"


def _run_registry() -> None:
    """Run the model registry scan, reconcile, and path registration."""
    try:
        import folder_paths  # type: ignore[import-untyped]
    except ImportError:
        print("comfygo_model_registry: folder_paths not available — skipping")
        return

    raw = getattr(folder_paths, "models_dir", None)
    if not raw:
        print("comfygo_model_registry: folder_paths.models_dir is not set — skipping")
        return

    models_dir = pathlib.Path(str(raw)).resolve()
    if not models_dir.is_dir():
        print(f"comfygo_model_registry: models_dir '{models_dir}' not found — skipping")
        return

    # Scan the model root plus legacy paths.
    legacy_roots: list[pathlib.Path] = []
    for legacy_sub in ("diffusers", "library"):
        legacy_path = models_dir / legacy_sub
        if legacy_path.is_dir():
            legacy_roots.append(legacy_path)

    packages = scanner.scan_models(models_dir, extra_roots=legacy_roots)
    identified = [p for p in packages if not p.ambiguous]

    # Always reconcile, even with zero identified packages,
    # so that stale views from removed models are pruned.
    report = reconciler.reconcile(identified, models_dir, dry_run=False)
    print("comfygo_model_registry: reconcile complete — " + report.summary)

    # Register view paths with ComfyUI's folder_paths.
    registered_categories: set[str] = set()
    for pkg in identified:
        for comp in pkg.components:
            for category in comp.comfy_categories:
                if category in registered_categories:
                    continue
                view_category_dir = compat_views.views_root(models_dir) / category
                if view_category_dir.is_dir():
                    folder_paths.add_model_folder_path(category, str(view_category_dir))
                    registered_categories.add(category)

    if registered_categories:
        cats = ", ".join(sorted(registered_categories))
        print(f"comfygo_model_registry: registered views for categories: {cats}")


# Run the registry at import time during ComfyUI startup unless a CLI or test
# process explicitly requests side-effect-free imports.
if os.environ.get("COMFYGO_MODEL_REGISTRY_AUTORUN", "1") != "0":
    _run_registry()
