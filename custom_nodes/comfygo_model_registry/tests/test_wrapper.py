"""Subprocess tests for the comfygo-models shell wrapper."""

from __future__ import annotations

import os
import pathlib
import subprocess

REPO_DIR = pathlib.Path(__file__).resolve().parents[3]
WRAPPER = REPO_DIR / "scripts" / "comfygo-models.sh"


def _make_diffusers_package(
    model_root: pathlib.Path,
    name: str = "SmokeModel",
) -> pathlib.Path:
    pkg = model_root / name
    (pkg / "transformer").mkdir(parents=True)
    (pkg / "model_index.json").write_text("{}")
    return pkg


def _run_wrapper(
    args: list[str],
    *,
    env_overrides: dict[str, str | None] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UV_CACHE_DIR"] = "/tmp/uv-cache"
    env.pop("COMFY_MODELS_DIR", None)
    env.pop("COMFYUI_DIR", None)
    if env_overrides:
        for key, value in env_overrides.items():
            if value is None:
                env.pop(key, None)
            else:
                env[key] = value

    return subprocess.run(
        [str(WRAPPER), *args],
        cwd=REPO_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_wrapper_routes_models_dir_before_reconcile(
    tmp_path: pathlib.Path,
) -> None:
    _make_diffusers_package(tmp_path)

    proc = _run_wrapper(["--models-dir", str(tmp_path), "reconcile"])

    assert proc.returncode == 0, proc.stderr
    assert "Dry-run reconcile:" in proc.stdout
    assert "view(s) created" in proc.stdout
    assert not (tmp_path / ".comfygo_views").exists()


def test_wrapper_routes_models_dir_before_reconcile_apply(
    tmp_path: pathlib.Path,
) -> None:
    pkg = _make_diffusers_package(tmp_path)

    proc = _run_wrapper(
        ["--models-dir", str(tmp_path), "reconcile", "--apply"]
    )

    assert proc.returncode == 0, proc.stderr
    link = tmp_path / ".comfygo_views/diffusion_models/SmokeModel/transformer"
    assert link.is_symlink()
    assert link.resolve() == (pkg / "transformer").resolve()


def test_wrapper_uses_comfyui_sibling_models_fallback(
    tmp_path: pathlib.Path,
) -> None:
    layout = tmp_path / "layout"
    code_dir = layout / "code"
    model_root = layout / "models"
    code_dir.mkdir(parents=True)
    pkg = _make_diffusers_package(model_root)

    proc = _run_wrapper(
        ["-f", "SmokeModel"],
        env_overrides={"COMFYUI_DIR": str(code_dir)},
    )

    assert proc.returncode == 0, proc.stderr
    assert "SmokeModel" in proc.stdout
    assert str(pkg.resolve()) in proc.stdout


def test_wrapper_empty_root_prints_configured_path(
    tmp_path: pathlib.Path,
) -> None:
    model_root = tmp_path / "empty-models"
    model_root.mkdir()

    proc = _run_wrapper(["--models-dir", str(model_root)])

    assert proc.returncode == 0, proc.stderr
    assert f"Model root(s): {model_root.resolve()}" in proc.stdout
    assert "Identified packages: 0" in proc.stdout
    assert not (model_root / ".comfygo_views").exists()
