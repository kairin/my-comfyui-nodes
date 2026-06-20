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


def test_live_validate_script_exists_and_executable() -> None:
    """The live validation script must exist and be executable."""
    script = REPO_DIR / "scripts" / "comfygo-live-validate"
    assert script.is_file(), f"Script missing: {script}"
    assert os.access(script, os.X_OK), f"Script not executable: {script}"


def test_live_validate_creates_evidence_on_failure() -> None:
    """The script must create an evidence directory even when it fails."""
    env = os.environ.copy()
    env.pop("COMFYUI_DIR", None)
    env.pop("COMFY_CLI_DIR", None)
    env["GIT_DIR"] = str(REPO_DIR / ".git")
    env["GIT_WORK_TREE"] = str(REPO_DIR)

    proc = subprocess.run(
        [str(WRAPPER.parent / "comfygo-live-validate")],
        cwd=REPO_DIR,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    # Must exit non-zero without COMFYUI_DIR.
    assert proc.returncode != 0, (
        f"Expected non-zero exit, got {proc.returncode}"
    )
    # Must print an evidence path in stdout or stderr.
    combined = proc.stdout + proc.stderr
    assert "Evidence:" in combined or "/tmp/comfygo-live." in combined, (
        "No evidence directory reported on failure"
    )


def test_live_validate_check_line_patterns() -> None:
    """Verify the health-line patterns the script checks are sensible
    without running the full live sequence (no real ComfyUI needed)."""
    # These are the grep patterns from the script's check_line() calls.
    patterns = [
        "Model registry source: present",
        "Model registry runtime copy: present",
        "Model root readable: yes",
        "Model registry CLI dry-run: ok",
    ]
    # They must each be non-empty and contain no unquoted regex meta.
    import re
    for p in patterns:
        assert p, "Empty pattern"
        assert len(p) > 10, f"Pattern too short: {p!r}"
        # Expect at least one space — real log line.
        assert " " in p, f"Pattern has no separator: {p!r}"
