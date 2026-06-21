"""Tests for the model root scanner — Diffusers inference, reserved folders, ambiguous detection."""

from __future__ import annotations

import json
import pathlib

from custom_nodes.comfygo_model_registry import models
from custom_nodes.comfygo_model_registry import scanner


def _make_diffusers_folder(
    root: pathlib.Path,
    name: str,
    subdirs: list[str] | None = None,
) -> pathlib.Path:
    """Create a Diffusers-style model folder with model_index.json."""
    folder = root / name
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "model_index.json").write_text(
        json.dumps({"model_index": True}), encoding="utf-8"
    )
    for sub in subdirs or []:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    return folder


class TestDiffusersInference:
    def test_full_diffusers_package(self, tmp_path: pathlib.Path) -> None:
        _make_diffusers_folder(
            tmp_path, "MyModel", subdirs=["transformer", "text_encoder", "vae"]
        )
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        pkg = pkgs[0]
        assert pkg.name == "MyModel"
        assert not pkg.ambiguous
        assert pkg.kind == models.ModelKind.DIFFUSERS
        assert pkg.detection_method == models.DetectionMethod.DIFFUSERS_INFERENCE
        assert len(pkg.components) == 3
        comp_names = {c.logical_name for c in pkg.components}
        assert comp_names == {"transformer", "text_encoder", "vae"}

    def test_partial_diffusers_package(self, tmp_path: pathlib.Path) -> None:
        """Only existing subdirectories should be inferred."""
        _make_diffusers_folder(tmp_path, "PartialModel", subdirs=["transformer"])
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        pkg = pkgs[0]
        assert not pkg.ambiguous
        assert len(pkg.components) == 1
        assert pkg.components[0].logical_name == "transformer"

    def test_diffusers_without_subdirs(self, tmp_path: pathlib.Path) -> None:
        """model_index.json with no expected subdirectories."""
        _make_diffusers_folder(tmp_path, "EmptyDiffusers")
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        pkg = pkgs[0]
        assert not pkg.ambiguous
        assert len(pkg.components) == 0

    def test_multiple_diffusers_packages(self, tmp_path: pathlib.Path) -> None:
        _make_diffusers_folder(tmp_path, "ModelA", subdirs=["transformer"])
        _make_diffusers_folder(tmp_path, "ModelB", subdirs=["vae"])
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 2
        names = {p.name for p in pkgs}
        assert names == {"ModelA", "ModelB"}


class TestReservedFolderSkipping:
    def test_skips_comfyui_category_folders(self, tmp_path: pathlib.Path) -> None:
        """Known ComfyUI category folder names must be skipped."""
        for name in [
            "diffusion_models",
            "text_encoders",
            "vae",
            "loras",
            "embeddings",
            "controlnet",
            "checkpoints",
        ]:
            (tmp_path / name).mkdir(exist_ok=True)
            # Place a model_index.json inside — still should be skipped.
            _make_diffusers_folder(
                tmp_path / name, "SomeModel", subdirs=["transformer"]
            )
        pkgs = scanner.scan_models(tmp_path)
        # None of the category folders themselves should appear as packages.
        assert len(pkgs) == 0

    def test_skips_hidden_folders(self, tmp_path: pathlib.Path) -> None:
        _make_diffusers_folder(tmp_path, ".hidden_model", subdirs=["transformer"])
        pkgs = scanner.scan_models(tmp_path)
        assert all(p.ambiguous for p in pkgs)

    def test_skips_dot_comfygo_views(self, tmp_path: pathlib.Path) -> None:
        """.comfygo_views directory must be skipped during model scanning."""
        (tmp_path / ".comfygo_views").mkdir()
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 0

    def test_case_insensitive_skip(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "Diffusion_Models").mkdir()
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 0


class TestAmbiguousDetection:
    def test_single_safetensors_file(self, tmp_path: pathlib.Path) -> None:
        folder = tmp_path / "MysteryModel"
        folder.mkdir()
        (folder / "random.safetensors").write_text("fake", encoding="utf-8")
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0].name == "MysteryModel"
        assert pkgs[0].ambiguous

    def test_empty_folder(self, tmp_path: pathlib.Path) -> None:
        (tmp_path / "EmptyFolder").mkdir()
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0].ambiguous

    def test_folder_with_only_readme(self, tmp_path: pathlib.Path) -> None:
        folder = tmp_path / "DocsOnly"
        folder.mkdir()
        (folder / "README.md").write_text("# Notes", encoding="utf-8")
        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        assert pkgs[0].ambiguous

    def test_multiple_ambiguous(self, tmp_path: pathlib.Path) -> None:
        for name in ["FolderA", "FolderB"]:
            (tmp_path / name).mkdir()
            (tmp_path / name / "data.bin").write_text("x", encoding="utf-8")
        pkgs = scanner.scan_models(tmp_path)
        ambiguous = [p for p in pkgs if p.ambiguous]
        assert len(ambiguous) == 2


class TestDescriptorPriority:
    def test_descriptor_overrides_diffusers_inference(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A comfygo-model.json must take precedence over model_index.json."""
        import json

        folder = tmp_path / "PriorityModel"
        folder.mkdir()
        # Both descriptor and model_index.json present.
        desc = {
            "schema": "comfygo.model.v1",
            "name": "PriorityModel",
            "kind": "lora",
            "components": {
                "adapter": {
                    "path": "adapter.safetensors",
                    "comfy_categories": ["loras"],
                }
            },
        }
        (folder / "comfygo-model.json").write_text(json.dumps(desc), encoding="utf-8")
        (folder / "model_index.json").write_text(
            json.dumps({"model_index": True}), encoding="utf-8"
        )
        (folder / "transformer").mkdir()

        pkgs = scanner.scan_models(tmp_path)
        assert len(pkgs) == 1
        pkg = pkgs[0]
        assert pkg.detection_method == models.DetectionMethod.DESCRIPTOR
        assert pkg.kind == models.ModelKind.LORA
        assert len(pkg.components) == 1
        assert pkg.components[0].logical_name == "adapter"
