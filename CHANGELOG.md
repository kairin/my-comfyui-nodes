# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project structure with vendored custom nodes and comfygo management scripts (from specs 001-003).
- Descriptor-first model registry (comfygo-model.json support, scanner, reconciler for .comfygo_views).
- GC safety harness and doctor flows (GCD scenarios 001-016).
- Guided comfygo doctor work in progress (see spec 004).
- Constitution updates for changelog (VIII) and branch protection/safety nets (IX).
- Up-front settings loader support in comfy-local (for 004 feature: patching, launch/tmux policy, enrichment, protection reminders).

### Changed
- Test scaffolding exclusions added to sync scripts and local-nodes patch to prevent runtime import issues during ComfyUI startup.
- Constitution version bumped to 1.2.0 with new principles.
- docs/workflow.md updated with accurate current GitHub protection state (from gh api) and aligned to T004/T005/T034.
- .pre-commit-config.yaml migrated to modern stages (pre-commit, pre-push); ruff scoped to owned code only (comfygo_model_registry + scripts) to respect Constitution I (no vendored edits).

### Fixed
- Test leakage into runtime custom_nodes that could cause "No module named 'pytest'" warnings at startup (affecting comfygo_model_registry and some vendored nodes' loaders).

### Changed
- Created `specs/004-comfygo-patched-tmux/tasks.md` following speckit process and approved plan.
- Created public GitHub issues #95, #96, #97 for key work items (high-level, privacy-safe).
- Updated `docs/workflow.md` with solo-maintainer "good enough" branch protection + Codacy recommendations.
- Reran constitution (v1.2.0) adding principles for Changelog and Branch Protection/Safety Nets; propagated to plan template.
- Seeded and enhanced 004 feature artifacts (spec, plan, tasks) and root CHANGELOG.

### Security / Ops
- Verified current GitHub branch protection (exists but minimal reviews/checks) and Codacy setup (Gate Policy + many tools active). Documented practical solo-maintainer settings (require PRs + status checks; 0 reviews; Codacy check required but grade not blocking). See issue #95 and workflow.md.

## [0.1.0] - 2026-06-20

### Added
- Speckit-driven development for model registry, GC, and doctor features.
- uv-first scripts and patches for comfy-cli local-nodes integration.
- Support for dumping models with descriptors and compatibility views.

[Unreleased]: https://github.com/kairin/my-comfyui-nodes/compare/main...HEAD
[0.1.0]: https://github.com/kairin/my-comfyui-nodes/releases/tag/v0.1.0 (initial structured history)