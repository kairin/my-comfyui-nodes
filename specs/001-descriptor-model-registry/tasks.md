---
description: "Task list for descriptor-model-registry feature implementation"
---

# Tasks: Descriptor-First Model Registry

**Input**: Design documents from `specs/001-descriptor-model-registry/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED — FR-016 mandates test coverage for descriptor parsing, Diffusers inference, reserved-folder skipping, symlink generation, idempotency, and conflict handling.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Custom node code**: `custom_nodes/comfygo_model_registry/`
- **Tests**: `custom_nodes/comfygo_model_registry/tests/`
- **CLI wrapper**: `scripts/comfygo-models.sh`
- **Docs**: `docs/model-library.md`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create `custom_nodes/comfygo_model_registry/` directory structure with `__init__.py`, `models.py`, `scanner.py`, `descriptor.py`, `reconciler.py`, `compat_views.py`, `tests/` subdir per plan.md source tree
- [X] T002 [P] Create the initial test package under `custom_nodes/comfygo_model_registry/tests/`; repo-root pytest importability is completed by T041

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 [P] Implement data classes (ModelPackage, ModelKind, DetectionMethod, ModelSource, Component, CompatibilityView, Descriptor, ComponentDescriptor) in `custom_nodes/comfygo_model_registry/models.py`
- [X] T004 [P] Implement `comfygo-model.json` descriptor parser with schema `comfygo.model.v1` validation in `custom_nodes/comfygo_model_registry/descriptor.py` — strict validation of required fields, forward-compatible acceptance of unknown fields
- [X] T005 [P] Implement Diffusers inference logic (`model_index.json` → `transformer`→`diffusion_models`, `text_encoder`→`text_encoders`, `vae`→`vae`) and model root scanner in `custom_nodes/comfygo_model_registry/scanner.py` — scan top-level folders, skip reserved ComfyUI category folders, skip hidden folders (except `.comfygo_views`), mark ambiguous folders
- [X] T006 Implement `.comfygo_views` directory manager in `custom_nodes/comfygo_model_registry/compat_views.py` — create/clean directory structure, generate relative symlinks
- [X] T007 Implement reconciler in `custom_nodes/comfygo_model_registry/reconciler.py` — dry-run and apply modes, symlink creation, stale symlink pruning, conflict detection and reporting, idempotent re-run
- [X] T008 Wire ComfyUI startup entry point in `custom_nodes/comfygo_model_registry/__init__.py` — scan at import time, reconcile, register generated paths via `folder_paths.add_model_folder_path()`, provide `NODE_CLASS_MAPPINGS` with a no-op node
- [X] T009 Write user-facing docs in `docs/model-library.md` covering canonical folder layout, descriptor schema reference, CLI commands, and troubleshooting

**Checkpoint**: Foundation ready — user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Descriptor-Based Model Detection (Priority: P1) 🎯 MVP

**Goal**: A Diffusers-style model folder placed under the model root is automatically detected and receives compatibility symlinks. Users place models once in their own folder; ComfyUI sees the components in the right categories.

**Independent Test**: Place a Diffusers folder with `model_index.json`, `transformer/`, `text_encoder/`, `vae/` under the model root. Run reconcile with `--apply`. Verify symlinks exist under `.comfygo_views/diffusion_models/<name>/`, `.comfygo_views/text_encoders/<name>/`, `.comfygo_views/vae/<name>/`.

### Tests for User Story 1 (REQUIRED — per FR-016)

- [X] T010 [P] [US1] Write test for descriptor parser: valid schema, missing fields, bad JSON, unknown schema version, forward-compatible unknown fields in `custom_nodes/comfygo_model_registry/tests/test_descriptor.py`
- [X] T011 [P] [US1] Write test for Diffusers inference: `model_index.json` with/without expected subdirectories, multiple packages, detection method flags in `custom_nodes/comfygo_model_registry/tests/test_scanner.py`
- [X] T012 [P] [US1] Write test for reserved folder skipping: known ComfyUI category names (`diffusion_models`, `text_encoders`, `vae`, `loras`, `embeddings`, `controlnet`, `checkpoints`), hidden folders, `.comfygo_views` exception in `custom_nodes/comfygo_model_registry/tests/test_scanner.py`
- [X] T013 [P] [US1] Write test for ambiguous folder rejection: single `.safetensors` file, single non-model file, empty directory, directory with only README in `custom_nodes/comfygo_model_registry/tests/test_scanner.py`
- [X] T014 [P] [US1] Write test for symlink generation: verify correct symlink paths, relative target resolution, cross-directory structure in `custom_nodes/comfygo_model_registry/tests/test_reconciler.py`
- [X] T015 [P] [US1] Write test for idempotency: re-running reconcile `--apply` produces identical state, no errors in `custom_nodes/comfygo_model_registry/tests/test_reconciler.py`
- [X] T016 [P] [US1] Write test for conflict handling: two packages with same name mapping to same category, first package wins, second reported as warning in `custom_nodes/comfygo_model_registry/tests/test_reconciler.py`

### Implementation for User Story 1

- [X] T017 [US1] Write verification: all US1 tests pass with `uv run pytest tests/ -v` in `custom_nodes/comfygo_model_registry/`
- [X] T018 [US1] Verify quickstart.md Scenario 1 (Diffusers detection), 5 (idempotency), 6 (stale pruning), 7 (ambiguous rejection) pass with real temp directory

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently — model detection + symlink generation works end-to-end. This is the MVP.

---

## Phase 4: User Story 2 - CLI Model Management (Priority: P2)

**Goal**: Users can inspect models and reconcile via `comfygo models` CLI commands. Dry-run is the default; `--apply` is explicit.

**Independent Test**: Run `comfygo models` — shows model root and summary. Run `comfygo models -f <filter>` — shows matching models and their category visibility. Run `comfygo models reconcile` — dry-run report without creating files. Run `comfygo models reconcile --apply` — creates symlinks.

### Tests for User Story 2 (REQUIRED — per FR-016)

- [X] T019 [P] [US2] Write test for CLI subcommands: `comfygo models`, `comfygo models -f <filter>`, `comfygo models reconcile`, `comfygo models reconcile --apply` in `custom_nodes/comfygo_model_registry/tests/test_cli.py`

### Implementation for User Story 2

- [X] T020 [P] [US2] Implement Python CLI module in `custom_nodes/comfygo_model_registry/cli.py` — model listing, filter matching, dry-run reconcile, apply reconcile
- [X] T021 [US2] Create `scripts/comfygo-models.sh` wrapper — delegate to Python module via `uv run`, parse args, respect `--models-dir` override, use `folder_paths.models_dir` as default
- [X] T022 [US2] Write verification: all US2 tests pass with `uv run pytest tests/ -v` in `custom_nodes/comfygo_model_registry/`
- [X] T023 [US2] Verify quickstart.md Scenario 2 (CLI listing), 3 (dry-run), 4 (apply) pass

**Checkpoint**: CLI management works independently — users can inspect and reconcile models without ComfyUI running.

---

## Phase 5: User Story 3 - Automatic Reconcile On Launch (Priority: P2)

**Goal**: `comfygo`, `comfygo start`, and `comfygo restart` automatically reconcile identifiable model packages before launching ComfyUI.

**Independent Test**: Add a new Diffusers folder under the model root. Run `comfygo start`. Before ComfyUI launches, compatibility views are created. Remove the folder, run `comfygo start` again — stale symlinks are pruned.

### Implementation for User Story 3

- [X] T024 [US3] Add auto-reconcile call before ComfyUI launch in `scripts/comfygo` (or the relevant launch wrapper) — run `comfygo-models.sh reconcile --apply` before launching ComfyUI
- [X] T025 [US3] Verify quickstart.md Scenario 8 (ComfyUI startup integration) passes — ensure `comfygo doctor` detects registry health

**Checkpoint**: Daily `comfygo` usage keeps model library in sync automatically.

---

## Phase 6: User Story 4 - Migration Support And Backward Compatibility (Priority: P3)

**Goal**: Existing model packages under legacy `models/diffusers/` continue to work. Category folders are not moved, copied, or deleted. A future migration command is deferred.

**Independent Test**: A Diffusers package under `models/diffusers/some-model/` is detected and receives compatibility views. The original `diffusers/` folder is not modified.

### Tests for User Story 4

- [X] T026 [P] [US4] Write test for legacy `diffusers/` path detection: model under `models/diffusers/name/` is detected the same as under `models/name/` in `custom_nodes/comfygo_model_registry/tests/test_scanner.py`
- [X] T052 [P] [US4] Add explicit SC-004 verification: reconcile `--apply` creates symlinks only under `.comfygo_views` and does not copy/move any model files
- [X] T053 [P] [US4] Add explicit SC-006 verification: legacy category payload files remain unchanged after reconcile/startup operations

### Implementation for User Story 4

- [X] T027 [US4] Add legacy `models/diffusers/*` and `models/library/*` as additional scan roots in `custom_nodes/comfygo_model_registry/scanner.py`
- [X] T028 [US4] Write verification: all tests pass with `uv run pytest -v`
- [X] T029 [US4] Run full integration test via quickstart.md — all 8 scenarios pass
- [X] T030 [US4] Verify `comfygo doctor` passes with the model registry present
- [X] T054 [P] [US4] Add shell-level `scripts/comfy-local doctor` verification for clean state, pending create, pending prune, and missing runtime-copy cases

**Checkpoint**: All user stories complete. Full backward compatibility maintained.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T031 [P] Finalize user-facing docs in `docs/model-library.md` — add examples for `comfygo-model.json`, `comfygo models` CLI usage, troubleshooting common issues
- [X] T032 Code cleanup and review — ensure uv-first commands throughout, no hard-coded absolute paths, no token leakage
- [X] T033 Run full test suite: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests -q` — all tests pass
- [X] T034 Run `comfygo doctor` and confirm clean bill of health
- [X] T035 Configure `.gitignore` to exclude `.comfygo_views/` patterns (they are runtime-generated, not part of this repo)

---

## Phase 8: Remediation — Adversarial-Review Fixes

**Purpose**: Address issues found during adversarial review; update all cross-artifact references

### P0 — Safety & Routing

- [X] T036 [P] Guard startup reconcile behind `COMFYGO_MODEL_REGISTRY_AUTORUN` env var in `custom_nodes/comfygo_model_registry/__init__.py` — skip `_run_registry()` if var is "0"; set to "0" in `scripts/comfygo-models.sh` before `uv run`
- [X] T037 [P] Add symlink escape validation for component targets in `custom_nodes/comfygo_model_registry/reconciler.py` — verify each resolved `target_path` is inside both the package root and the model root via filesystem containment checks; skip and warn on escape
- [X] T038 [P] Add symlinked views-root/category/model-dir safety check in `custom_nodes/comfygo_model_registry/compat_views.py` — reject if `.comfygo_views` is itself a symlink; skip symlinked category/model dirs during prune
- [X] T039 Route `comfygo` / `comfygo restart` daily launch through the Python registry (`scripts/comfygo-models.sh`) instead of legacy shell logic in `scripts/comfy-local` — ensure LoRA/GGUF/checkpoint descriptors work in daily flow
- [X] T040 [P] Fix idempotency reporting in `custom_nodes/comfygo_model_registry/compat_views.py` — existing correct symlinks return `None` instead of the link path so they are not counted as "created"

### P1 — Tests & Importability

- [X] T041 [P] Add `pytest.ini` at repo root with `[pytest] pythonpath = .` so `uv run pytest custom_nodes/comfygo_model_registry/tests -q` works without manual `PYTHONPATH=`
- [X] T042 [P] Write test for symlinked `.comfygo_views` root rejection in `custom_nodes/comfygo_model_registry/tests/test_compat_views.py`
- [X] T043 [P] Write test for component symlink escape detection in `custom_nodes/comfygo_model_registry/tests/test_reconciler.py`
- [X] T044 [P] Write test for `COMFYGO_MODEL_REGISTRY_AUTORUN` guard: prove CLI dry-run creates no `.comfygo_views` in `custom_nodes/comfygo_model_registry/tests/test_cli.py`
- [X] T045 [P] Write test for unchanged idempotency reporting (existing correct symlinks → zero "created") in `custom_nodes/comfygo_model_registry/tests/test_reconciler.py`
- [X] T046 [P] Verify `git diff --check` passes and `__pycache__` is cleaned

### P1 — Cross-Artifact Consistency

- [X] T047 [P] Update `specs/001-descriptor-model-registry/contracts/README.md` CLI section to use `comfygo models -f/--filter <name>`
- [X] T048 [P] Update `specs/001-descriptor-model-registry/quickstart.md`:
  - Scenario 2: `scripts/comfygo-models.sh TestModel` → `scripts/comfygo-models.sh -f TestModel`
  - Scenario 5: "Same output as first run" → "No new views; all existing views unchanged"
  - Test command: `PYTHONPATH=. uv run pytest` → `uv run pytest` (after pytest.ini)
- [X] T049 [P] Update `specs/001-descriptor-model-registry/plan.md`:
  - Constitution Check: add gates for symlink escape, env guard, Python routing
  - Source tree: `test_models.py` → `test_cli.py`, add `test_compat_views.py`
- [X] T050 [P] Update `docs/model-library.md` for public-repo safety:
  - Replace concrete local model paths with `$COMFYUI_MODELS_DIR`
  - Replace model-specific examples with generic `owner/example-model` / `Example-Model-Package`
  - Use `comfygo models -f/--filter <name>` in CLI docs
- [X] T051 [P] Define concrete "registry health" checks for `comfygo doctor` — list which checks must pass (registry source present, runtime copy present, CLI wrapper dry-run works, model root readable)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **US1 (Phase 3)**: Depends on Foundational — MVP, no dependencies on other stories
- **US2 (Phase 4)**: Depends on Foundational — CLI calls into scanner/reconciler from Phase 2
- **US3 (Phase 5)**: Depends on US2 (CLI script) — auto-reconcile calls the CLI
- **US4 (Phase 6)**: Depends on Foundational — adds scan roots to scanner
- **Polish (Phase 7)**: Depends on all user stories complete

### User Story Dependencies

- **US1 (P1)**: Can start after Foundational — No dependencies on other stories ⭐ MVP
- **US2 (P2)**: Can start after Foundational — Independent of US1, but offers a better MVP together with US1
- **US3 (P2)**: Depends on US2 — auto-reconcile launch integration leverages the CLI
- **US4 (P3)**: Can start after Foundational — Independent legacy path scanning

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD pattern where applicable)
- Symlink generation before CLI integration
- CLI integration before auto-reconcile launch
- Backward compatibility tested last
- Remediation dependency order: T036 must complete before T044; T037 and T038
  must complete before T042 and T043; T040 must complete before T045.

### Parallel Opportunities

- T001–T002 (Setup): all parallel
- T003–T009 (Foundational): T003, T004, T005 can run in parallel; T005 and T006 can run in parallel once models are done; T007 depends on compat_views; T008 depends on scanner+reconciler
- All test tasks in US1 marked [P] can run in parallel
- US2 and US4 can start in parallel after Foundational (US2 depends on scanner/reconciler; US4 only needs scanner)
- US3 depends on US2 CLI wrapper

---

## Parallel Example: User Story 1 (MVP)

```bash
# Launch all test files for US1 together:
Task: "Write test_descriptor.py"
Task: "Write test_scanner.py"
Task: "Write test_reconciler.py"

# After tests pass, verify integration:
Task: "Run all US1 scenarios from quickstart.md"
```

## Parallel Example: User Story 2 (After US1)

```bash
# CLI module and wrapper are independent of most US1 test work:
Task: "Implement cli.py"
Task: "Create comfygo-models.sh wrapper"

# After both, test:
Task: "Run CLI test suite"
Task: "Verify quickstart CLI scenarios"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational
3. Complete Phase 3: User Story 1 (model detection + symlink views)
4. **STOP and VALIDATE**: Run full test suite, verify quickstart Scenarios 1, 5, 6, 7
5. Deploy/demo: model detection works end-to-end

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add US1 (Model Detection) → **MVP!** — users can place models and get symlinks
3. Add US2 (CLI) → users can inspect and reconcile from terminal
4. Add US3 (Auto-reconcile) → daily `comfygo` keeps model library in sync
5. Add US4 (Migration) → legacy paths work transparently
6. Polish → docs, cleanup, final verification

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: US1 (Model Detection — highest priority)
   - Developer B: US2 (CLI) — can start after scanner/reconciler
   - Developer C: US4 (Migration) — can start after scanner
3. Developer A finishes US1 → verify integration
4. Developer B completes US2 → Developer A/B integrate US3 (auto-reconcile)
5. Developer C completes US4 → final integration test

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests use `pytest` via `uv run pytest` — no direct `pytest` or `python -m pytest` commands
- No model files, tokens, or local absolute paths are committed
- All Python commands use uv-first forms throughout
- Commit after each task or logical group
- Stop at US1 checkpoint to validate MVP independently
