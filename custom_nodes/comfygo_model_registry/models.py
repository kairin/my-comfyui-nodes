"""Data classes for the comfygo model registry."""

from __future__ import annotations

import dataclasses
import enum
import pathlib
import re
from typing import Optional

# Segment names that are unsafe for filesystem path construction.
_SEGMENT_DENY_RE = re.compile(r"[/\\]|(?:^|/)\.\.(?:$|$|[/\\])|^~")


def validate_path_segment(segment: str, *, context: str = "") -> None:
    """Raise ValueError if *segment* contains path separators or traversal.

    Callers should pass a short *context* label for error messages.
    """
    if not segment or _SEGMENT_DENY_RE.search(segment):
        raise ValueError(f"Unsafe path segment{context}: {segment!r}")


class ModelKind(enum.Enum):
    """Recognized model types."""

    DIFFUSERS = "diffusers"
    LORA = "lora"
    EMBEDDING = "embedding"
    CHECKPOINT = "checkpoint"
    VAE = "vae"
    TEXT_ENCODER = "text_encoder"
    CONTROLNET = "controlnet"
    GGUF = "gguf"
    OTHER = "other"


class DetectionMethod(enum.Enum):
    """How a model package was identified."""

    DESCRIPTOR = "descriptor"
    DIFFUSERS_INFERENCE = "diffusers_inference"
    UNKNOWN = "unknown"


@dataclasses.dataclass(frozen=True)
class ModelSource:
    """Origin metadata for a model package."""

    type: str  # huggingface, civitai, local, or other
    repo: Optional[str] = None
    version: Optional[str] = None


@dataclasses.dataclass(frozen=True)
class ComponentDescriptor:
    """A component entry within a comfygo-model.json descriptor."""

    path: str
    comfy_categories: list[str]


@dataclasses.dataclass(frozen=True)
class Descriptor:
    """Parsed comfygo-model.json (schema comfygo.model.v1)."""

    schema_: str
    name: str
    kind: str
    source: Optional[ModelSource] = None
    components: dict[str, ComponentDescriptor] = dataclasses.field(default_factory=dict)
    notes: Optional[str] = None
    workflows: list[str] = dataclasses.field(default_factory=list)
    preview_images: list[str] = dataclasses.field(default_factory=list)
    documentation: list[str] = dataclasses.field(default_factory=list)


@dataclasses.dataclass(frozen=True)
class Component:
    """A subdirectory or file within a model package mapped to ComfyUI categories."""

    logical_name: str
    relative_path: pathlib.Path
    comfy_categories: list[str]

    def resolved_path(self, package_path: pathlib.Path) -> pathlib.Path:
        """Resolve the component path relative to the package root."""
        return (package_path / self.relative_path).resolve()

    def exists(self, package_path: pathlib.Path) -> bool:
        """Check whether the component path actually exists on disk."""
        return self.resolved_path(package_path).exists()


@dataclasses.dataclass(frozen=True)
class CompatibilityView:
    """A generated symlink exposing a component to a ComfyUI category."""

    category: str
    model_name: str
    component_name: str
    target_path: pathlib.Path


@dataclasses.dataclass
class ModelPackage:
    """A folder under the model root that is self-identifying as a model."""

    name: str
    path: pathlib.Path
    kind: ModelKind = ModelKind.OTHER
    source: Optional[ModelSource] = None
    components: list[Component] = dataclasses.field(default_factory=list)
    descriptor: Optional[Descriptor] = None
    detection_method: DetectionMethod = DetectionMethod.UNKNOWN

    @property
    def ambiguous(self) -> bool:
        """True when the folder cannot be identified."""
        return self.detection_method == DetectionMethod.UNKNOWN
