"""comfygo-model.json descriptor parser with schema comfygo.model.v1 validation."""

from __future__ import annotations

import json
import pathlib
from typing import Optional

from . import models

SUPPORTED_SCHEMA = "comfygo.model.v1"

# Recognized model kind strings mapped to ModelKind enum.
_KIND_MAP: dict[str, models.ModelKind] = {
    "diffusers": models.ModelKind.DIFFUSERS,
    "lora": models.ModelKind.LORA,
    "embedding": models.ModelKind.EMBEDDING,
    "checkpoint": models.ModelKind.CHECKPOINT,
    "vae": models.ModelKind.VAE,
    "text_encoder": models.ModelKind.TEXT_ENCODER,
    "controlnet": models.ModelKind.CONTROLNET,
    "gguf": models.ModelKind.GGUF,
    "other": models.ModelKind.OTHER,
}


def parse_descriptor(path: pathlib.Path) -> Optional[models.Descriptor]:
    """Parse and validate a comfygo-model.json file.

    Returns a Descriptor on success, or None if the file is missing,
    invalid, or uses an unsupported schema version.
    """
    if not path.is_file():
        return None

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"Warning: failed to parse {path}: {exc}")
        return None

    if not isinstance(raw, dict):
        print(f"Warning: {path} is not a JSON object")
        return None

    schema = raw.get("schema")
    if schema != SUPPORTED_SCHEMA:
        if schema is not None:
            print(f"Warning: {path} has unsupported schema '{schema}' — skipping")
        else:
            print(f"Warning: {path} is missing 'schema' field — skipping")
        return None

    # Validate the descriptor name is a safe path segment.
    name = raw.get("name")
    if not isinstance(name, str) or not name.strip():
        print(f"Warning: {path} is missing required 'name' field — skipping")
        return None
    try:
        models.validate_path_segment(name.strip(), context=" (descriptor 'name')")
    except ValueError:
        print(f"Warning: {path} has unsafe 'name' field — skipping")
        return None

    kind_str = raw.get("kind")
    if not isinstance(kind_str, str) or kind_str not in _KIND_MAP:
        print(f"Warning: {path} has invalid or missing 'kind' field — skipping")
        return None

    raw_components = raw.get("components")
    if not isinstance(raw_components, dict) or not raw_components:
        print(f"Warning: {path} is missing or has empty 'components' — skipping")
        return None

    components: dict[str, models.ComponentDescriptor] = {}
    for comp_name, comp_raw in raw_components.items():
        if not isinstance(comp_raw, dict):
            print(
                f"Warning: {path}: component '{comp_name}' is not an object — skipping"
            )
            continue
        comp_path = comp_raw.get("path")
        comp_cats = comp_raw.get("comfy_categories")
        if not isinstance(comp_path, str) or not comp_path.strip():
            print(
                f"Warning: {path}: component '{comp_name}' missing valid 'path' — "
                f"skipping"
            )
            continue
        if not isinstance(comp_cats, list) or not comp_cats:
            print(
                f"Warning: {path}: component '{comp_name}' missing valid "
                f"'comfy_categories' — skipping"
            )
            continue
        if comp_path.startswith("/") or ".." in comp_path.split("/"):
            print(
                f"Warning: {path}: component '{comp_name}' path '{comp_path}' "
                f"is not relative — skipping"
            )
            continue
        # Validate component name and categories as safe path segments.
        try:
            models.validate_path_segment(comp_name, context=" (component name)")
        except ValueError:
            print(f"Warning: {path}: component name '{comp_name}' is unsafe — skipping")
            continue
        categories: list[str] = []
        for cat in comp_cats:
            cat_str = str(cat)
            try:
                models.validate_path_segment(cat_str, context=" (category)")
            except ValueError:
                print(f"Warning: {path}: category '{cat_str}' is unsafe — skipping")
                continue
            categories.append(cat_str)
        if not categories:
            print(
                f"Warning: {path}: component '{comp_name}' has no valid "
                f"categories — skipping"
            )
            continue
        components[comp_name] = models.ComponentDescriptor(
            path=comp_path,
            comfy_categories=categories,
        )

    if not components:
        print(f"Warning: {path}: no valid components found — skipping")
        return None

    source = None
    raw_source = raw.get("source")
    if isinstance(raw_source, dict):
        source = models.ModelSource(
            type=str(raw_source.get("type", "unknown")),
            repo=raw_source.get("repo"),
            version=raw_source.get("version"),
        )

    return models.Descriptor(
        schema_=schema,
        name=name.strip(),
        kind=kind_str,
        source=source,
        components=components,
        notes=raw.get("notes"),
        workflows=raw.get("workflows", []),
        preview_images=raw.get("preview_images", []),
        documentation=raw.get("documentation", []),
    )


def descriptor_to_package(
    descriptor: models.Descriptor,
    folder_path: pathlib.Path,
) -> models.ModelPackage:
    """Convert a parsed Descriptor into a ModelPackage.

    The package is always marked as DESCRIPTOR-based detection.
    """
    kind = _KIND_MAP.get(descriptor.kind, models.ModelKind.OTHER)
    components = [
        models.Component(
            logical_name=name,
            relative_path=pathlib.Path(cd.path),
            comfy_categories=list(cd.comfy_categories),
        )
        for name, cd in descriptor.components.items()
    ]
    return models.ModelPackage(
        name=descriptor.name,
        path=folder_path,
        kind=kind,
        source=descriptor.source,
        components=components,
        descriptor=descriptor,
        detection_method=models.DetectionMethod.DESCRIPTOR,
    )
