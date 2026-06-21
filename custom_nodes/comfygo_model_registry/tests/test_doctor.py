"""Subprocess tests for `scripts/comfy-local` doctor registry health checks."""

from __future__ import annotations

import os
import pathlib
import subprocess

REPO_DIR = pathlib.Path(__file__).resolve().parents[3]
COMFY_LOCAL_SCRIPT = REPO_DIR / "scripts" / "comfy-local"


def _make_fake_comfyui_dir(
    repo_dir: pathlib.Path, tmp_root: pathlib.Path
) -> pathlib.Path:
    """Create a fake ComfyUI checkout with vendored custom_nodes."""
    comfyui_dir = tmp_root / "comfyui"
    source_nodes = repo_dir / "custom_nodes"
    target_nodes = comfyui_dir / "custom_nodes"
    target_nodes.mkdir(parents=True)

    for entry in source_nodes.iterdir():
        target = target_nodes / entry.name
        target.symlink_to(entry, target_is_directory=entry.is_dir())

    (comfyui_dir / ".git").mkdir()
    return comfyui_dir


def _make_fake_comfy_cli_dir(tmp_root: pathlib.Path) -> pathlib.Path:
    """Create a fake comfy-cli checkout."""
    cli_dir = tmp_root / "comfy-cli"
    (cli_dir / ".git").mkdir(parents=True)
    return cli_dir


def _run_comfy_local_doctor(
    *,
    tmp_root: pathlib.Path,
    comfyui_dir: pathlib.Path,
    comfy_cli_dir: pathlib.Path,
    models_dir: pathlib.Path,
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "UV_CACHE_DIR": "/tmp/uv-cache",
            "COMFY_LOCAL_CONFIG": str(tmp_root / "comfy-local.env"),
            "COMFYUI_DIR": str(comfyui_dir),
            "COMFY_CLI_DIR": str(comfy_cli_dir),
            "COMFY_MODELS_DIR": str(models_dir),
        }
    )
    # Prevent loading real local envrc files from this working tree.
    pathlib.Path(env["COMFY_LOCAL_CONFIG"]).write_text("", encoding="utf-8")

    if extra_env:
        env.update(extra_env)

    return subprocess.run(
        [str(COMFY_LOCAL_SCRIPT), "doctor"],
        cwd=REPO_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def _make_diffusers_package(models_dir: pathlib.Path, name: str = "SmokeModel") -> None:
    package = models_dir / name
    (package / "transformer").mkdir(parents=True)
    (package / "model_index.json").write_text("{}", encoding="utf-8")


def test_doctor_passes_clean_with_no_pending_registry_changes(
    tmp_path: pathlib.Path,
) -> None:
    comfyui_dir = _make_fake_comfyui_dir(REPO_DIR, tmp_path)
    comfy_cli_dir = _make_fake_comfy_cli_dir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    proc = _run_comfy_local_doctor(
        tmp_root=tmp_path,
        comfyui_dir=comfyui_dir,
        comfy_cli_dir=comfy_cli_dir,
        models_dir=models_dir,
    )

    assert proc.returncode == 0, proc.stderr
    assert "Model registry CLI dry-run: ok" in proc.stdout
    assert "Model registry CLI dry-run: pending changes" not in proc.stdout


def test_doctor_fails_when_registry_reports_pending_create_changes(
    tmp_path: pathlib.Path,
) -> None:
    comfyui_dir = _make_fake_comfyui_dir(REPO_DIR, tmp_path)
    comfy_cli_dir = _make_fake_comfy_cli_dir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    _make_diffusers_package(models_dir, "PendingModel")

    proc = _run_comfy_local_doctor(
        tmp_root=tmp_path,
        comfyui_dir=comfyui_dir,
        comfy_cli_dir=comfy_cli_dir,
        models_dir=models_dir,
    )

    assert proc.returncode != 0
    assert "Model registry CLI dry-run: pending changes" in proc.stdout


def test_doctor_fails_when_registry_reports_pending_pruned_views(
    tmp_path: pathlib.Path,
) -> None:
    comfyui_dir = _make_fake_comfyui_dir(REPO_DIR, tmp_path)
    comfy_cli_dir = _make_fake_comfy_cli_dir(tmp_path)
    models_dir = tmp_path / "models"
    stale = (
        models_dir
        / ".comfygo_views"
        / "diffusion_models"
        / "StaleModel"
        / "old.safetensors"
    )
    stale.parent.mkdir(parents=True)
    stale.write_text("stale", encoding="utf-8")
    models_dir.mkdir(parents=True, exist_ok=True)

    proc = _run_comfy_local_doctor(
        tmp_root=tmp_path,
        comfyui_dir=comfyui_dir,
        comfy_cli_dir=comfy_cli_dir,
        models_dir=models_dir,
    )

    assert proc.returncode != 0
    assert "Model registry CLI dry-run: pending changes" in proc.stdout
    assert stale.exists()
    assert stale.read_text(encoding="utf-8") == "stale"


def test_doctor_fails_when_registry_reports_conflict(
    tmp_path: pathlib.Path,
) -> None:
    comfyui_dir = _make_fake_comfyui_dir(REPO_DIR, tmp_path)
    comfy_cli_dir = _make_fake_comfy_cli_dir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()
    _make_diffusers_package(models_dir, "ConflictModel")
    conflicting_view = (
        models_dir
        / ".comfygo_views"
        / "diffusion_models"
        / "ConflictModel"
        / "transformer"
    )
    conflicting_view.parent.mkdir(parents=True)
    conflicting_view.write_text("not a generated symlink", encoding="utf-8")

    proc = _run_comfy_local_doctor(
        tmp_root=tmp_path,
        comfyui_dir=comfyui_dir,
        comfy_cli_dir=comfy_cli_dir,
        models_dir=models_dir,
    )

    assert proc.returncode != 0
    assert "Model registry CLI dry-run: pending changes" in proc.stdout
    assert conflicting_view.exists()
    assert conflicting_view.read_text(encoding="utf-8") == "not a generated symlink"


def test_doctor_fails_when_runtime_registry_copy_missing(
    tmp_path: pathlib.Path,
) -> None:
    comfyui_dir = _make_fake_comfyui_dir(REPO_DIR, tmp_path)
    runtime_registry = comfyui_dir / "custom_nodes" / "comfygo_model_registry"
    runtime_registry.unlink()
    comfy_cli_dir = _make_fake_comfy_cli_dir(tmp_path)
    models_dir = tmp_path / "models"
    models_dir.mkdir()

    proc = _run_comfy_local_doctor(
        tmp_root=tmp_path,
        comfyui_dir=comfyui_dir,
        comfy_cli_dir=comfy_cli_dir,
        models_dir=models_dir,
    )

    assert proc.returncode != 0
    assert "Model registry runtime copy: missing" in proc.stdout
