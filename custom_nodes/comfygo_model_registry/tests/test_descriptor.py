"""Tests for the comfygo-model.json descriptor parser."""

from __future__ import annotations

import json
import pathlib
import tempfile

import pytest

from custom_nodes.comfygo_model_registry import descriptor


def _write_descriptor(dir: pathlib.Path, data: dict) -> pathlib.Path:
    path = dir / "comfygo-model.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


class TestParseDescriptor:
    def test_valid_descriptor(self, tmp_path: pathlib.Path) -> None:
        data = {
            "schema": "comfygo.model.v1",
            "name": "Test Model",
            "kind": "diffusers",
            "source": {
                "type": "huggingface",
                "repo": "test/repo",
            },
            "components": {
                "unet": {
                    "path": "transformer",
                    "comfy_categories": ["diffusion_models"],
                },
                "encoder": {
                    "path": "text_encoder",
                    "comfy_categories": ["text_encoders"],
                },
            },
            "notes": "test notes",
            "workflows": ["test_workflow.json"],
        }
        path = _write_descriptor(tmp_path, data)
        desc = descriptor.parse_descriptor(path)
        assert desc is not None
        assert desc.schema_ == "comfygo.model.v1"
        assert desc.name == "Test Model"
        assert desc.kind == "diffusers"
        assert desc.source is not None
        assert desc.source.type == "huggingface"
        assert desc.source.repo == "test/repo"
        assert len(desc.components) == 2
        assert desc.components["unet"].path == "transformer"
        assert desc.components["unet"].comfy_categories == ["diffusion_models"]
        assert desc.notes == "test notes"
        assert desc.workflows == ["test_workflow.json"]

    def test_missing_schema(self, tmp_path: pathlib.Path) -> None:
        data = {"name": "No Schema", "kind": "diffusers", "components": {}}
        path = _write_descriptor(tmp_path, data)
        assert descriptor.parse_descriptor(path) is None

    def test_unsupported_schema(self, tmp_path: pathlib.Path) -> None:
        data = {
            "schema": "comfygo.model.v999",
            "name": "Bad",
            "kind": "diffusers",
            "components": {"x": {"path": ".", "comfy_categories": ["x"]}},
        }
        path = _write_descriptor(tmp_path, data)
        assert descriptor.parse_descriptor(path) is None

    def test_missing_name(self, tmp_path: pathlib.Path) -> None:
        data = {
            "schema": "comfygo.model.v1",
            "kind": "diffusers",
            "components": {"x": {"path": ".", "comfy_categories": ["x"]}},
        }
        path = _write_descriptor(tmp_path, data)
        assert descriptor.parse_descriptor(path) is None

    def test_invalid_kind(self, tmp_path: pathlib.Path) -> None:
        data = {
            "schema": "comfygo.model.v1",
            "name": "Bad Kind",
            "kind": "not-a-valid-kind",
            "components": {"x": {"path": ".", "comfy_categories": ["x"]}},
        }
        path = _write_descriptor(tmp_path, data)
        assert descriptor.parse_descriptor(path) is None

    def test_empty_components(self, tmp_path: pathlib.Path) -> None:
        data = {
            "schema": "comfygo.model.v1",
            "name": "Empty Components",
            "kind": "diffusers",
            "components": {},
        }
        path = _write_descriptor(tmp_path, data)
        assert descriptor.parse_descriptor(path) is None

    def test_component_path_escape(self, tmp_path: pathlib.Path) -> None:
        """Component paths with '..' or leading '/' must be rejected."""
        data = {
            "schema": "comfygo.model.v1",
            "name": "Escape Attempt",
            "kind": "diffusers",
            "components": {
                "bad": {
                    "path": "../outside",
                    "comfy_categories": ["diffusion_models"],
                }
            },
        }
        path = _write_descriptor(tmp_path, data)
        desc = descriptor.parse_descriptor(path)
        # The bad component should be skipped, resulting in no valid components.
        assert desc is None

    def test_forward_compatible_unknown_fields(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Unknown top-level fields must not cause rejection."""
        data = {
            "schema": "comfygo.model.v1",
            "name": "Forward Compat",
            "kind": "lora",
            "components": {
                "adapter": {
                    "path": "adapter.safetensors",
                    "comfy_categories": ["loras"],
                }
            },
            "future_field": "should be accepted",
        }
        path = _write_descriptor(tmp_path, data)
        desc = descriptor.parse_descriptor(path)
        assert desc is not None
        assert desc.name == "Forward Compat"

    def test_invalid_json(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "comfygo-model.json"
        path.write_text("not valid json", encoding="utf-8")
        assert descriptor.parse_descriptor(path) is None

    def test_missing_file(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "nonexistent.json"
        assert descriptor.parse_descriptor(path) is None


class TestPathTraversalRejection:
    """Descriptors with path-traversal attempts must be rejected."""

    def test_category_traversal(self) -> None:
        """Category containing ../../ must be rejected at parse time."""
        desc_json = {
            "schema": "comfygo.model.v1",
            "name": "SafeName",
            "kind": "diffusers",
            "components": {
                "bad": {
                    "path": "transformer",
                    "comfy_categories": ["../../outside"],
                }
            },
        }
        with tempfile.TemporaryDirectory() as td:
            desc_path = pathlib.Path(td) / "comfygo-model.json"
            desc_path.write_text(json.dumps(desc_json))
            result = descriptor.parse_descriptor(desc_path)
            # The unsafe category is stripped from the component; the component
            # then has zero valid categories, so the descriptor is rejected.
            assert result is None

    def test_model_name_traversal(self) -> None:
        """Model name containing ../ must be rejected."""
        desc_json = {
            "schema": "comfygo.model.v1",
            "name": "../escape",
            "kind": "diffusers",
            "components": {
                "transformer": {
                    "path": "transformer",
                    "comfy_categories": ["diffusion_models"],
                }
            },
        }
        with tempfile.TemporaryDirectory() as td:
            desc_path = pathlib.Path(td) / "comfygo-model.json"
            desc_path.write_text(json.dumps(desc_json))
            result = descriptor.parse_descriptor(desc_path)
            assert result is None  # Unsafe name → rejected.

    def test_component_name_traversal(self) -> None:
        """Component key containing / must be rejected."""
        desc_json = {
            "schema": "comfygo.model.v1",
            "name": "SafeModel",
            "kind": "diffusers",
            "components": {
                "../escape": {
                    "path": "transformer",
                    "comfy_categories": ["diffusion_models"],
                }
            },
        }
        with tempfile.TemporaryDirectory() as td:
            desc_path = pathlib.Path(td) / "comfygo-model.json"
            desc_path.write_text(json.dumps(desc_json))
            result = descriptor.parse_descriptor(desc_path)
            # The component was rejected but the model still parses
            # with zero components (which then makes it invalid).
            if result is not None:
                assert len(result.components) == 0


class TestDescriptorToPackage:
    def test_conversion(self) -> None:
        from custom_nodes.comfygo_model_registry import models

        desc = models.Descriptor(
            schema_="comfygo.model.v1",
            name="Converted Model",
            kind="lora",
            source=models.ModelSource(type="civitai", repo="test/lora"),
            components={
                "adapter": models.ComponentDescriptor(
                    path="adapter.safetensors",
                    comfy_categories=["loras"],
                ),
            },
        )
        pkg = descriptor.descriptor_to_package(desc, pathlib.Path("/models/test"))
        assert pkg.name == "Converted Model"
        assert pkg.kind == models.ModelKind.LORA
        assert pkg.detection_method == models.DetectionMethod.DESCRIPTOR
        assert len(pkg.components) == 1
        assert pkg.components[0].logical_name == "adapter"
        assert pkg.components[0].comfy_categories == ["loras"]
