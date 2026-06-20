# Implementation Plan: Descriptor-First Model Registry

**Branch**: `001-descriptor-model-registry` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-descriptor-model-registry/spec.md`

## Summary

Implement a descriptor-first model registry for this vendored ComfyUI setup.
Canonical model folders under the ComfyUI models directory become the source of
truth — each model lives in its own folder as downloaded, with either a
`comfygo-model.json` descriptor or (for Diffusers packages) a `model_index.json`
that the system infers from. Compatibility symlinks under `.comfygo_views/`
expose model components to ComfyUI's existing category-based node system.
A `comfygo models` CLI provides inspection, dry-run reconcile, and apply
commands. Automatic reconcile runs before `comfygo`/`comfygo start`/`comfygo restart`
launches ComfyUI. No model files are copied, moved, or deleted.

Technical approach: a vendored Python package (`comfygo_model_registry`) that
scans the model root at startup, creates/updates `.comfygo_views/` with
symlinks, and registers generated paths with ComfyUI's `folder_paths` module.
A separate `scripts/comfygo-models.sh` wrapper (or inline shell function)
provides the CLI surface.

## Technical Context

**Language/Version**: Python 3.11+ (ComfyUI workspace Python)

**Primary Dependencies**:
- ComfyUI (`folder_paths` module — available at custom-node runtime)
- Python stdlib: `os`, `json`, `pathlib`, `shutil`
- CLI: `argparse` (stdlib — no external CLI framework needed for v1)

**Storage**: Filesystem — model files on disk, symlinks under `.comfygo_views/`

**Testing**: `pytest` via `uv run pytest` against the vendorable Python package

**Target Platform**: Linux (ComfyUI deployment target — POSIX symlink semantics)

**Project Type**: Library (vendored ComfyUI custom node + CLI wrapper)

**Performance Goals**: Models directory scan completes in under 2 seconds for
~100 model folders. Symlink generation is idempotent and sub-second.

**Constraints**:
- Symlinks must stay inside configured model root.
- No model file copying, moving, or deleting.
- uv-first for all Python and comfy-cli commands.
- No absolute paths in this repo (use `folder_paths.models_dir` or env vars).
- Reserved ComfyUI category folders and hidden folders must be skipped.
- Ambiguous single-file folders must not be guessed.

**Scale/Scope**: Single-user ComfyUI instance, ~10–100 model folders.
First pass covers Diffusers inference and `comfygo-model.json` descriptors.
Future scope (not in v1): migration from legacy category folders, GUI.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Vendored source of truth**: The `comfygo_model_registry` custom node and
  CLI scripts are written in this repo first, then synced into the live
  ComfyUI runtime. No direct edits to the live custom_nodes copy.
- **Explicit upstream refresh**: The registry does not fetch or update any
  upstream model repositories. Model management is orthogonal to node and
  patch updates.
- **Safe daily operation**: `comfygo models reconcile --apply` is the only
  mutable operation, and it only creates symlinks. Automatic reconcile before
  launch is read-only for model files. Dry-run is the default.
- **Patch durability**: The custom node is a full vendored copy, not a patch.
  CLI behavior is delivered through vendored scripts that work without
  comfy-cli patches.
- **Public repo safety and secret safety**: No tokens, model weights, logs,
  caches, runtime histories, or absolute local paths are committed. Model
  root config uses `folder_paths.models_dir` or env vars.
- **Symlink confinement**: Symlinks must stay inside the configured model
  root. Component target paths are validated with a resolved filesystem
  containment check at reconcile time — escaped targets are skipped with a
  warning. `.comfygo_views` and its subdirectories are checked for being
  symlinks before any operation.
- **Env-guarded startup reconcile**: `__init__.py` startup reconcile is gated
  behind `COMFYGO_MODEL_REGISTRY_AUTORUN`. The CLI wrapper sets this to "0"
  so that import-time side effects do not mutate the model root during
  `comfygo models` commands.
- **Python-registry routing**: `comfygo` / `comfygo restart` auto-reconcile
  routes through the Python `comfygo_model_registry` module, not through
  legacy shell logic, ensuring all descriptor types (LoRA, GGUF, checkpoints)
  are visible in daily operation.
- **uv-first execution**: Tests and scripts use `uv run` and `uv pip` forms.
  No direct `pip`, `python -m pip`, or unwrapped `python` commands.
- **Verifiable runtime behavior**: `comfygo doctor` verifies registry health:
  source package present in this repo, runtime copy present after sync, model
  root readable, `uv` available, and CLI dry-run side-effect-free. `comfygo
  models reconcile` is dry-run by default. Tests cover descriptor parsing,
  inference, symlink generation, idempotency, and conflict handling.

**Gate verdict**: PASS — no violations. Complexity tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/001-descriptor-model-registry/
├── plan.md              # This file
├── research.md          # Phase 0 — technical research
├── data-model.md        # Phase 1 — entity model
├── quickstart.md        # Phase 1 — validation guide
├── contracts/           # Phase 1 — interface contracts (descriptor schema)
├── checklists/          # Specification quality checklists
│   └── requirements.md
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
custom_nodes/comfygo_model_registry/
├── __init__.py                  # ComfyUI node entry: scans, reconciles, registers paths
├── scanner.py                   # Model root scanner: package detection + inference
├── descriptor.py                # comfygo-model.json parsing + schema validation
├── reconciler.py                # Symlink generation, pruning, conflict handling
├── models.py                    # Data classes: ModelPackage, Component, CompatibilityView
├── compat_views.py              # .comfygo_views directory management
├── cli.py                       # Python CLI module
└── tests/
    ├── test_scanner.py
    ├── test_descriptor.py
    ├── test_reconciler.py
    ├── test_cli.py
    └── test_compat_views.py

scripts/
├── comfygo-models.sh            # comfygo models CLI entry point
└── install-model-registry.sh    # (optional) symlink the registry into ComfyUI

docs/
└── model-library.md             # User-facing docs for the model library (already exists)
```

**Structure Decision**: Single-project layout. The vendored custom node lives at
`custom_nodes/comfygo_model_registry/` following the existing project convention.
CLI wrapper in `scripts/` follows the existing `comfygo` script pattern. No
separate `src/` directory is needed — `custom_nodes/comfygo_model_registry/` IS
the source, mirroring how ComfyUI custom nodes are structured.

## Complexity Tracking

*Not needed — Constitution Check passed with no violations.*
