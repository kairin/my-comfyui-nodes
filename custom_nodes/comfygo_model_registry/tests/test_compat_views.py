"""Tests for .comfygo_views safety helpers."""

from __future__ import annotations

import pathlib

from custom_nodes.comfygo_model_registry import compat_views
from custom_nodes.comfygo_model_registry import models


def test_create_view_rejects_symlinked_views_root(
    tmp_path: pathlib.Path,
) -> None:
    """create_view must not write through a symlinked .comfygo_views root."""
    target = tmp_path / "Model" / "transformer"
    target.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    compat_views.views_root(tmp_path).symlink_to(outside, target_is_directory=True)
    view = models.CompatibilityView(
        category="diffusion_models",
        model_name="Model",
        component_name="transformer",
        target_path=target,
    )

    result = compat_views.create_view(tmp_path, view)

    assert result is None
    assert not (outside / "diffusion_models").exists()


def test_remove_stale_views_skips_symlinked_category(
    tmp_path: pathlib.Path,
) -> None:
    """Prune must not traverse symlinked category directories."""
    vroot = compat_views.views_root(tmp_path)
    vroot.mkdir()
    outside = tmp_path / "outside-category"
    outside.mkdir()
    (vroot / "diffusion_models").symlink_to(outside, target_is_directory=True)

    removed = compat_views.remove_stale_views(tmp_path, set())

    assert removed == 0
    assert (vroot / "diffusion_models").is_symlink()
