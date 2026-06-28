# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `comfygo workflow apply` — apply JSON patch ops with auto-checkpoint and optional `--validate` (spec 007).
- `comfygo workflow checkpoint list|restore` — rollback snapshots under `.comfygo_debug/checkpoints/`.
- `comfygo workflow diagnose` — read-only JSON report for agent workflow review (`--workflow`, `--prompt-id`, `--latest-error`; spec 006).
- Guided `comfygo doctor` with Comfygo readiness, Checks, Actions, Recommended next action, and `--apply` with GCD gate (`scripts/comfy-local`, spec 004 Phase 15).
- Shared 16 GCD scenario harness (`scripts/comfygo-gcd-harness.sh`) used by doctor and `scripts/comfygo-verify`.
- Doctor options: `--models-dir`, `--keep-evidence`, `--smoke-repatch`, `--yes` for non-interactive apply.
- `scripts/speckit-progress.py` task progress diagnostic for speckit convergence tracking.
- Headless model-root auto-enrichment during launch when `COMFYGO_ENRICH_CIVITAI=1` via `--scan-models-root` in `scripts/hf_select_download.py`.
- Initial project structure with vendored custom nodes and comfygo management scripts (specs 001–003).
- Descriptor-first model registry (`comfygo-model.json`, scanner, reconciler for `.comfygo_views`).
- Constitution principles VIII (changelog) and IX (branch protection/safety nets).
- Up-front settings loader in `scripts/comfy-local` (patching, launch/tmux, enrichment, protection keys).

### Changed
- `comfygo doctor` runs 16 GCD scenarios by default and blocks `--apply` until `PASS: all 16`.
- Launch sequence skips re-patch when tmux target is active (avoids disrupting running ComfyUI per spec edge case).
- Launch auto-enrichment uses structured manifest parsing and real `hf_select_download.py` integration (not stub).
- `patch_drift_check` parses `## Historical Names` in manifests and emits exact Error and Exit Contract messages.
- `scripts/comfygo-verify` Phase 3 delegates to shared GCD harness (no duplicated scenario logic).
- README, `docs/workflow.md`, and `docs/model-library.md` lead with `comfygo` as single entry point (spec 005).
- Constitution III reinforced with single entry point principle (version 1.2.1).
- `.pre-commit-config.yaml`: ruff scoped to owned code; verify-quality hook sets `VERIFY_QUALITY_INVOKED_BY_PRE_COMMIT=1`.
- `docs/workflow.md` updated with solo-maintainer branch protection + Codacy recommendations.
- Test scaffolding exclusions in sync scripts and local-nodes patch.

### Fixed
- Pre-commit hang: `verify-quality.sh` no longer recursively invokes pre-commit when run from the verify-quality hook.
- Launch re-patch drift for `comfy-cli-patches` now checks `COMFY_CLI_DIR` (not `COMFYUI_DIR`).
- Launch auto-enrichment no longer fails non-interactively with `repo is required unless --resume-from is used` over SSH.
- Doctor user-facing run lines use `comfygo` instead of `scripts/comfygo`.
- Test leakage into runtime `custom_nodes` causing `No module named 'pytest'` warnings at startup.

### Security / Ops
- GitHub branch protection: require PRs + Codacy analysis check; 0 required reviews (solo maintainer). See `docs/workflow.md`.

## [0.1.0] - 2026-06-20

### Added
- Speckit-driven development for model registry, GC, and doctor features.
- uv-first scripts and patches for comfy-cli local-nodes integration.
- Support for dumping models with descriptors and compatibility views.

[Unreleased]: https://github.com/kairin/my-comfyui-nodes/compare/main...HEAD
[0.1.0]: https://github.com/kairin/my-comfyui-nodes/releases/tag/v0.1.0 (initial structured history)
