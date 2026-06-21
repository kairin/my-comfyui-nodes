# Safety Requirements Quality Checklist: model-gc

**Purpose**: Validate the quality, clarity, completeness, and consistency of the safety and data-protection requirements for the GC feature (dry-run default, explicit targeting, marker semantics, symlink/path safety, rename-only mutation, unique-match, no-bulk, no-prune-trash, etc.). This is "unit tests for the requirements" — not implementation verification.
**Created**: 2026-06-20
**Feature**: [specs/002-model-gc/spec.md](spec.md)
**Last re-validated**: 2026-06-21 (post-clarification convergence)

**Note**: Items test whether the *requirements themselves* are well-specified, not whether the code will work.

## Safety Invariants & Marker Semantics

- [x] CHK001 Are the rules that marker files (`.comfygo-download.json` or `comfygo-model.json`) mean only "comfygo knows this folder" — and explicitly do **NOT** mean the folder is disposable or safe to remove — stated clearly and repeated in key sections (User Stories, Key Entities, FRs)? [Clarity, Completeness, Spec §Key Entities, FR-002]
- [x] CHK002 Is the "marker ≠ garbage" principle consistently enforced in acceptance scenarios and error cases (e.g., no automatic or bulk removal based on marker presence alone)? [Consistency, FR-002, SC-003]
- [x] CHK003 Does the spec explicitly require that GC MUST NOT quarantine folders without an explicit `-f NAME --apply` (dry-run is the only default behavior)? [Completeness, FR-001, FR-002]

## Explicit Targeting & Prevention of Bulk / Accidental Operations

- [x] CHK004 Is it unambiguously specified that `-f NAME --apply` must resolve to *exactly one* managed folder, and that zero, ambiguous-only, or multiple managed matches must result in an error with no mutation? [Clarity, Measurability, FR-013, SC-010]
- [x] CHK005 Are the exact error messages and exit behavior for "no managed match", "ambiguous-only", and "multiple managed matches" defined in the requirements (and contracts)? [Completeness, FR-013]
- [x] CHK006 Is the requirement that `--apply` without `-f NAME` must fail with a specific error and create no `.comfygo_trash/` documented? [Completeness, FR-001]

## Source Symlink, Path, and Trash Safety

- [x] CHK007 Are requirements for refusing to quarantine a source folder whose top-level entry is a symlink clearly defined: unfiltered dry-run reports a warning and exits 0, while filtered dry-run or apply targeting only source symlinks exits 1 with the same warning? [Completeness, FR-004, FR-014, SC-011]
- [x] CHK008 Is the full set of symlink safety checks for the trash destination (root, date dir, destination path) and "treat symlinks as collisions" specified? [Completeness, FR-006, FR-011]
- [x] CHK009 Is the v1 rule that GC MUST NOT prune, delete, or walk `.comfygo_trash/` contents (only create dated dir + explicit rename allowed) explicitly stated as a constraint? [Clarity, FR-007]
- [x] CHK010 Are cross-filesystem rename failure requirements (report error, leave source unchanged, no copy+delete fallback) measurable and consistently placed? [Clarity, Measurability, FR-010, SC-008]

## Mutation Constraints (Rename-Only, Idempotency, Collision)

- [x] CHK011 Are the requirements that the *only* allowed mutation is `os.rename()` (no copy, no delete, no shutil, no merge) stated without ambiguity? [Clarity, FR-005, FR-010]
- [x] CHK012 Is collision handling (append `-1`, `-2`, never overwrite, treat existing symlink/dir/file as collision) fully specified? [Completeness, FR-011]
- [x] CHK013 Are idempotency requirements clear for repeated `gc -f <name> --apply` after successful quarantine (must report no-managed-match or "nothing to do" and perform no further mutation)? [Clarity, FR-008, SC-005]

## Reporting, Skipped Entries, and Dry-Run Accuracy

- [x] CHK014 Are the exact categories to report in dry-run (Managed with marker type, Ambiguous, Skipped with reason including "source symlink") and their silence rules (reserved/hidden) specified? [Completeness, FR-003, FR-004]
- [x] CHK015 Is the behavior for empty/unparseable marker files (still treated as Managed + warning) explicitly required? [Clarity, Edge Case, SC-001 related]

## Scope Boundaries & Non-Overlap

- [x] CHK016 Is the v1 scope restriction (top-level model root folders only; no legacy `extra_roots`, no recursion into subdirs) stated as an intentional constraint with rationale? [Clarity, FR-015]
- [x] CHK017 Are the independence requirements between GC and `reconcile` (GC does not touch `.comfygo_views/`, reconcile does not manage real folders) clear? [Consistency, FR-009]
- [x] CHK018 Are assumptions about model root location (`folder_paths.models_dir` or env var) and same-filesystem trash documented? [Completeness, Assumptions]

## Constitution & Repository Policy Alignment (Requirements Level)

- [x] CHK019 Are the uv-first command requirements (no direct `python`/`pip`) and public-repo safety rules (no hard-coded absolute paths, use `folder_paths.models_dir` or env) explicitly required in the GC spec/plan? [Completeness, Constitution VI & V]
- [x] CHK020 Is it clear that GC is a manual-only command and must not run automatically during `comfygo`, start, restart, or doctor? [Clarity, Assumptions]

## Edge Cases & Failure Modes

- [x] CHK021 Are requirements for destination collision involving symlinks, existing files, or directories defined? [Edge Case, FR-011]
- [x] CHK022 Is the behavior on permission/read-only filesystem failures (report + leave source unchanged) specified? [Completeness, FR-010, SC-007]
- [x] CHK023 Are repeated apply safety and "already quarantined" reporting requirements (no mutation on second apply) covered? [Edge Case, FR-008]

## Notes

- Check items off as completed: `[x]`
- Add comments or findings inline with references to spec sections or adversarial review items.
- Items are numbered sequentially (CHK001+). Append to this file for future safety-focused checklist runs rather than overwriting.
- This checklist focuses on whether the *safety requirements are well written*, not on whether the future implementation passes tests.
