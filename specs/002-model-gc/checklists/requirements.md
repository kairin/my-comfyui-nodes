# Specification Quality Checklist: model-gc

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-06-20
**Feature**: [specs/002-model-gc/spec.md](spec.md)
**Last re-validated**: 2026-06-20 (after adversarial review remediation)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## P0 Items Resolved

All issues from adversarial review have been applied:

- Removed trash symlink pruning from v1 (FR-007 redefined).
- Added unique-match apply rule (FR-013) — `-f NAME --apply` must resolve to exactly one managed folder.
- Added source symlink refusal (FR-014) — GC refuses to quarantine symlinked source folders.
- Added v1 top-level-only scan scope (FR-015) — no legacy `extra_roots` scanning.
- Fixed data-model.md: `list[Maker]` → `list[Marker]`, removed `ambiguous: bool` from `ManagedFolder`, added `SkippedFolder`.
- Added explicit safety checks to T007 instead of "reuse pattern".
- T005 now uses raw `iterdir()` with symlink check — no `scanner.scan_models()` usage.
- Added missing test tasks: T036 (invalid marker), T037 (multi-match apply), T038 (source symlink), T039 (`gc --apply` without `-f`).
- Removed `shutil` from plan dependencies.
- Contracts pinned with exact error messages and exit codes.
- Quickstart uses temp directories and adds multi-match safety scenario.
- Research documents top-level-only scan, unique-match rule, and source symlink refusal.
- Independent post-remediation audit (see adversarial-review.md) confirmed all critical proposals from the review have been addressed. Feature is ready for implementation.
