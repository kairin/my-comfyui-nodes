"""Model root scanner: package detection and Diffusers inference."""

from __future__ import annotations

import pathlib
from typing import Optional

from . import models
from . import descriptor

# ComfyUI category folder names that must be skipped as model roots.
_RESERVED_CATEGORY_FOLDERS: set[str] = {
    "diffusion_models",
    "text_encoders",
    "vae",
    "loras",
    "embeddings",
    "controlnet",
    "checkpoints",
    "upscale_models",
    "ipadapter",
    "insightface",
    "ultralytics",
    "style_models",
    "hypernetworks",
    "gligen",
    "classifiers",
    "mmdets",
    "onnx",
    "photomaker",
    "animatediff_models",
    "animatediff_motion_lora",
    "sams",
    "facedetection",
    "depth",
    "groundingdino",
    "clip",
    "clip_vision",
    "unet",
    "diffusers",
}


def scan_models(
    models_dir: pathlib.Path,
    extra_roots: Optional[list[pathlib.Path]] = None,
) -> list[models.ModelPackage]:
    """Scan the model root and return all detected model packages.

    Scans top-level folders under *models_dir* and any *extra_roots*.
    Skips reserved category folders and hidden folders (dot-prefixed).
    Returns a list of ModelPackage — ambiguous packages are marked with
    detection_method=UNKNOWN.
    """
    roots = [models_dir]
    if extra_roots:
        roots.extend(extra_roots)

    seen_names: dict[str, pathlib.Path] = {}
    packages: list[models.ModelPackage] = []

    for root in roots:
        if not root.is_dir():
            continue
        for entry in sorted(root.iterdir()):
            if not entry.is_dir():
                continue
            name = entry.name

            # Skip reserved category folders.
            if name.lower() in _RESERVED_CATEGORY_FOLDERS:
                continue

            # Skip hidden folders (dot-prefixed).
            if name.startswith("."):
                continue

            # Avoid scanning the same folder name from multiple roots.
            if name in seen_names:
                continue
            seen_names[name] = entry

            pkg = _identify_package(entry)
            packages.append(pkg)

    return packages


def _identify_package(folder: pathlib.Path) -> models.ModelPackage:
    """Try to identify a single folder as a model package.

    Resolution order:
      1. comfygo-model.json descriptor (primary)
      2. model_index.json (Diffusers inference)
      3. → ambiguous (unknown)
    """
    # 1. Descriptor check.
    desc_path = folder / "comfygo-model.json"
    desc = descriptor.parse_descriptor(desc_path)
    if desc is not None:
        return descriptor.descriptor_to_package(desc, folder)

    # 2. Diffusers inference.
    model_index_path = folder / "model_index.json"
    if model_index_path.is_file():
        return _infer_diffusers_package(folder)

    # 3. Mark ambiguous.
    return models.ModelPackage(
        name=folder.name,
        path=folder.resolve(),
        detection_method=models.DetectionMethod.UNKNOWN,
    )


def _infer_diffusers_package(folder: pathlib.Path) -> models.ModelPackage:
    """Infer a Diffusers-style model package from model_index.json."""
    components: list[models.Component] = []

    _DIFFUSERS_INFERENCE_MAP: dict[str, list[str]] = {
        "transformer": ["diffusion_models"],
        "text_encoder": ["text_encoders"],
        "vae": ["vae"],
    }

    for logical_name, categories in _DIFFUSERS_INFERENCE_MAP.items():
        comp_path = folder / logical_name
        if comp_path.is_dir():
            components.append(
                models.Component(
                    logical_name=logical_name,
                    relative_path=pathlib.Path(logical_name),
                    comfy_categories=list(categories),
                )
            )

    return models.ModelPackage(
        name=folder.name,
        path=folder.resolve(),
        kind=models.ModelKind.DIFFUSERS,
        components=components,
        detection_method=models.DetectionMethod.DIFFUSERS_INFERENCE,
    )
