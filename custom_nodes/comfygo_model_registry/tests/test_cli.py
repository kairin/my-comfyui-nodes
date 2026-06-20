"""Tests for the CLI module — arg parsing and command dispatch."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys

from custom_nodes.comfygo_model_registry import cli
from custom_nodes.comfygo_model_registry import scanner


def test_cli_filter_list(tmp_path: pathlib.Path) -> None:
    """comfygo models -f Qwen should filter packages."""
    # Create a Diffusers-style package.
    pkg = tmp_path / "Qwen-Image-Edit"
    pkg.mkdir()
    (pkg / "model_index.json").write_text("{}")
    (pkg / "transformer").mkdir()
    (pkg / "text_encoder").mkdir()
    (pkg / "vae").mkdir()

    # Also create an unrelated package that should be filtered out.
    other = tmp_path / "SomeOtherModel"
    other.mkdir()
    (other / "model_index.json").write_text("{}")

    packages = scanner.scan_models(tmp_path)
    # Filter should match Qwen.
    matched = [p for p in packages if not p.ambiguous and "Qwen" in p.name]
    assert len(matched) == 1
    assert matched[0].name == "Qwen-Image-Edit"


def test_cli_filter_no_match(tmp_path: pathlib.Path) -> None:
    """comfygo models -f NonExistent should print no matches."""
    pkg = tmp_path / "RealModel"
    pkg.mkdir()
    (pkg / "model_index.json").write_text("{}")

    packages = scanner.scan_models(tmp_path)
    matched = [p for p in packages if not p.ambiguous and "NonExistent" in p.name]
    assert len(matched) == 0


def test_cli_argparse_list_no_filter() -> None:
    """Parse: comfygo models (no arguments)."""
    parser = cli.build_parser()
    args = parser.parse_args([])
    assert args.command is None
    assert args.filter is None


def test_cli_argparse_list_filter() -> None:
    """Parse: comfygo models -f Qwen."""
    parser = cli.build_parser()
    args = parser.parse_args(["-f", "Qwen"])
    assert args.command is None
    assert args.filter == "Qwen"


def test_cli_argparse_long_filter() -> None:
    """Parse: comfygo models --filter Qwen."""
    parser = cli.build_parser()
    args = parser.parse_args(["--filter", "Qwen"])
    assert args.command is None
    assert args.filter == "Qwen"


def test_cli_argparse_reconcile_dry_run() -> None:
    """Parse: comfygo models reconcile."""
    parser = cli.build_parser()
    args = parser.parse_args(["reconcile"])
    assert args.command == "reconcile"
    assert args.filter is None
    assert args.apply is False
    assert getattr(args, "reconcile_filter", None) is None


def test_cli_argparse_reconcile_filter() -> None:
    """Parse: comfygo models reconcile -f Qwen."""
    parser = cli.build_parser()
    args = parser.parse_args(["reconcile", "-f", "Qwen"])
    assert args.command == "reconcile"
    assert getattr(args, "reconcile_filter") == "Qwen"


def test_cli_argparse_reconcile_filter_apply() -> None:
    """Parse: comfygo models reconcile -f Qwen --apply."""
    parser = cli.build_parser()
    args = parser.parse_args(["reconcile", "-f", "Qwen", "--apply"])
    assert args.command == "reconcile"
    assert getattr(args, "reconcile_filter") == "Qwen"
    assert args.apply is True


def test_cli_argparse_reconcile_apply_only() -> None:
    """Parse: comfygo models reconcile --apply."""
    parser = cli.build_parser()
    args = parser.parse_args(["reconcile", "--apply"])
    assert args.command == "reconcile"
    assert args.apply is True
    assert getattr(args, "reconcile_filter") is None


def test_cli_argparse_models_dir() -> None:
    """Parse: comfygo models --models-dir /tmp."""
    parser = cli.build_parser()
    args = parser.parse_args(["--models-dir", "/tmp"])
    assert args.models_dir == "/tmp"


def test_cli_get_models_dir_override() -> None:
    """get_models_dir with explicit override."""
    d = cli.get_models_dir("/tmp/test_models")
    assert d == pathlib.Path("/tmp/test_models").resolve()


def test_cli_list_has_no_view_side_effects(
    tmp_path: pathlib.Path,
) -> None:
    """comfygo models listing must not create .comfygo_views."""
    pkg = tmp_path / "ListedModel"
    pkg.mkdir()
    (pkg / "model_index.json").write_text("{}")
    (pkg / "transformer").mkdir()

    cli.main(["--models-dir", str(tmp_path)])

    assert not (tmp_path / ".comfygo_views").exists()


def test_autorun_guard_skips_registry_when_disabled(
    tmp_path: pathlib.Path,
) -> None:
    """COMFYGO_MODEL_REGISTRY_AUTORUN=0 prevents startup registry execution."""
    model_root = tmp_path / "models"
    pkg = model_root / "ObservableModel"
    (pkg / "transformer").mkdir(parents=True)
    (pkg / "model_index.json").write_text("{}")
    registry_call_marker = tmp_path / "registry-called"
    repo_dir = pathlib.Path(__file__).resolve().parents[3]

    code = r"""
import json
import pathlib
import sys
import types

models_dir = pathlib.Path(sys.argv[1])
marker = pathlib.Path(sys.argv[2])

folder_paths = types.ModuleType("folder_paths")
folder_paths.models_dir = str(models_dir)

def add_model_folder_path(category, path):
    marker.write_text(f"{category}:{path}")

folder_paths.add_model_folder_path = add_model_folder_path
sys.modules["folder_paths"] = folder_paths

import custom_nodes.comfygo_model_registry  # noqa: F401

print(json.dumps({
    "registry_called": marker.exists(),
    "views_exist": (models_dir / ".comfygo_views").exists(),
}))
"""
    env = os.environ.copy()
    env["COMFYGO_MODEL_REGISTRY_AUTORUN"] = "0"
    env["PYTHONPATH"] = (
        str(repo_dir)
        if not env.get("PYTHONPATH")
        else f"{repo_dir}{os.pathsep}{env['PYTHONPATH']}"
    )

    proc = subprocess.run(
        [sys.executable, "-c", code, str(model_root), str(registry_call_marker)],
        cwd=repo_dir,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    observed = json.loads(proc.stdout)
    assert observed == {"registry_called": False, "views_exist": False}
