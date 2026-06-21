# Implementation Plan: Model Garbage Collection (comfygo models gc)

**Branch**: `002-model-gc` | **Date**: 2026-06-20 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-model-gc/spec.md`

## Summary

Add a safe, marker-based garbage collection command for model folders.
`comfygo models gc` reports managed folders, ambiguous folders, and
safety warnings without modifying anything. With `-f NAME --apply`, it
quarantines explicitly selected folders to `.comfygo_trash/<date>/<name>/`.
The feature uses raw top-level model-root directory enumeration so source
paths are not resolved through symlinks. It reuses the registry's reserved
folder policy and path validation helpers, but not `scanner.scan_models()` for
GC move-source discovery. GC does not normalize downloaded folder names into
short model-root aliases such as `<kind>-NNN`; that belongs to a separate
install/normalization behavior that can preserve identity through JSON
metadata. Unsafe source names fail closed during quarantine with a controlled
error and no mutation.

## Technical Context

**Language/Version**: Python 3.11+ (ComfyUI workspace Python)

**Primary Dependencies**:
- Existing `custom_nodes/comfygo_model_registry/` — reuse reserved-folder
  policy and path validation helpers
- Python stdlib: `os`, `pathlib`, `json`, `datetime`
- CLI: `argparse` — extend the existing `cli.py` parser

**Storage**: Filesystem — model folder rename operations

**Testing**: `pytest` via `uv run pytest` — add to existing test suite

**Target Platform**: Linux (POSIX rename semantics)

**Project Type**: CLI subcommand (extension of existing `comfygo models`)

**Performance Goals**: GC scan completes in under 1 second for ~100 model folders.
Each quarantine operation is a single `os.rename()` — sub-second per folder.

**Constraints**:
- Only act on folders with ownership markers (`.comfygo-download.json`
  or `comfygo-model.json`)
- Require explicit `-f NAME --apply` for any destructive action
- Fail closed on cross-filesystem quarantine — no copy+delete fallback
- Skip reserved ComfyUI category folders, hidden folders
- .comfygo_trash path components validated against symlink traversal
- Source folder names that fail path-segment validation produce controlled
  errors; GC does not rename them into safe root aliases
- Destination collision: append collision-suffix, never overwrite
- Folder normalization/install naming such as `<kind>-NNN` is explicitly
  out of scope for this GC command

**Scale/Scope**: Single-user ComfyUI instance, ~10–100 model folders.
V1 only: explicit-target quarantine. No `--all-owned` or automatic
bulk cleanup until a later version adds explicit opt-in flags.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Vendored source of truth**: The GC command extends the existing
  `comfygo_model_registry` vendored custom node and CLI. All changes
  made in this repo first, then synced into the live runtime.
- **Explicit upstream refresh**: GC does not fetch any upstream models
  or update any node/patch code. It operates only on local filesystem state.
- **Safe daily operation**: Dry-run is the default. `--apply` requires
  an explicit `-f NAME` target — no bulk operations. Quarantine renames
  rather than deletes, with no copy+delete fallback.
- **Public repo safety**: GC does not read tokens, network, or secrets.
  Model root paths use `folder_paths.models_dir` or env vars.
- **uv-first execution**: All Python commands use `uv run` forms.
- **Verifiable runtime behavior**: Dry-run reports what GC would do.
  `comfygo doctor` health checks unaffected — GC is a separate command.

**Gate verdict**: PASS — no violations. Complexity tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-model-gc/
├── plan.md              # This file
├── research.md          # Phase 0 — technical research
├── data-model.md        # Phase 1 — entity model
├── quickstart.md        # Phase 1 — validation guide
├── contracts/           # Phase 1 — interface contracts (CLI, safety helpers)
├── checklists/          # Specification quality checklists
│   ├── requirements.md
│   └── safety.md
├── doctor-matrix.md     # Scriptable GC safety/doctor scenario matrix
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
custom_nodes/comfygo_model_registry/
├── __init__.py          # (unchanged — GC does not run at startup)
├── cli.py               # EXTEND: add gc subcommand parser + dispatch
├── gc.py                # NEW: GC logic — scan, report, quarantine
├── scanner.py           # REUSE: reserved-folder policy only
├── descriptor.py        # Existing descriptor parser; GC only checks marker presence
├── reconciler.py        # REUSE: view safety helpers
├── models.py            # REUSE: validate_path_segment()
├── compat_views.py      # REUSE: validate_path_segment, views_root helper
└── tests/
    ├── test_gc.py       # NEW: GC tests
    ├── test_cli.py      # EXTEND: GC CLI regression coverage
    └── test_wrapper.py  # EXTEND: GC wrapper regression coverage
```

**Structure Decision**: Extend the existing `custom_nodes/comfygo_model_registry/`
package with a new `gc.py` module. No new package. CLI integration via the
existing `cli.py` argparser. This minimizes new surface area and reuses all
existing safety infrastructure.

## Complexity Tracking

*Not needed — Constitution Check passed with no violations.*

## Post-Plan Adversarial Review (2026-06-20)

After this plan and the initial tasks.md were generated, a dedicated multi-agent adversarial review was performed.

See `adversarial-review.md` (in this directory) for:
- Consolidated findings from three read-only adversarial agents (data-loss, clarity, feasibility).
- Concrete proposals for every identified gap (including wording fixes already partially applied to tasks.md).
- Exact location of the review artifact and recommended remediation order.

Key outcome: the P0 classification, gate, symlink-safety, unique-match,
top-level-only, and FR-007 "no trash pruning" fixes have been folded back into
the spec/plan/tasks/contracts. Implementation may proceed from the dry-run
MVP first.

The review is part of the permanent feature record.

## Low-Tier Agent Assignment Notes

`tasks.md` is the canonical actionable task list. This section is only a
coordination map for assigning the current T001-T082 tasks to smaller agents;
it must not be treated as a separate backlog.

### Current Task Groups

- **Setup**: T001-T004 create `gc.py`, `test_gc.py`, the CLI parser, and
  wrapper forwarding coverage.
- **Foundational safety**: T005-T010 implement GC data classes, marker
  detection, raw top-level scan, trash safety, collision handling, and
  rename-only quarantine primitives.
- **US1 verification**: T011-T014 confirm reconcile stale-view pruning stays
  independent of GC.
- **US2 dry-run MVP**: T015-T030 add dry-run tests, report formatting,
  filter behavior, raw-scan enforcement, and CLI dispatch.
- **US3 explicit apply**: T031-T050 add quarantine tests, `--apply` gates,
  unique-match behavior, failure handling, and no trash pruning.
- **US4 ambiguous reporting**: T051-T057 make ambiguous, reserved, hidden,
  and source-symlink behavior explicit.
- **Polish**: T058-T067 cover docs, full test run, whitespace checks,
  cache cleanup, `.gitignore`, quickstart, and final analyze.
- **Phase 8 convergence remediation**: T068-T079 cover public path cleanup,
  reserved-folder policy reuse, raw GC CLI dispatch, source-symlink contract
  warnings, primitive quarantine hardening, data-model alignment, collision
  warnings, filtered no-match exit behavior, integration tests, docs,
  trailing-whitespace verification, and performance-smoke validation.
- **Phase 9 convergence remediation**: T080 covers unsafe source folder names
  that fail path-segment validation, requiring controlled GC errors with no
  traceback, no source mutation, and no trash creation.
- **Phase 10 requirements quality closure**: T081-T082 align unsafe-name
  wording across spec/quickstart/contracts/tasks and close the
  normalization-boundary checklist with supporting artifact evidence.

### Non-Negotiable Implementation Constraints

- GC folder discovery uses raw `models_dir.iterdir()` over top-level entries.
  Do not call `scanner.scan_models()` and do not use scanner package data or
  `packages.ambiguous` for GC classification.
- GC may reuse the existing scanner reserved-folder policy, either by
  importing the reserved list/helper or by moving that policy into a shared
  helper. That reuse is only for skip decisions.
- CLI dispatch should call `gc.run_gc(models_dir, filter_str=..., apply=...)`
  directly, or use an equivalent `cmd_gc(models_dir, filter_str, apply)`
  wrapper. Do not pass scanner packages into GC.
- The only mutating apply path is creating the required trash directories and
  one `os.rename()` of the explicitly selected managed folder. No copy/delete
  fallback and no trash pruning in v1.
- GC must not normalize or reinstall source folders into short names such as
  `<kind>-NNN`; if a source folder name is unsafe for quarantine destination
  construction, report a controlled error and leave normalization to a separate
  install feature.
