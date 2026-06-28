# Tasks: Workflow Diagnose CLI

**Input**: Design documents from `specs/006-workflow-diagnose/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

## Phase 1: Setup

- [X] T001 Create fixture workflow `specs/006-workflow-diagnose/fixtures/invalid_vae.json` for quickstart
- [X] T002 [P] Add `.comfygo_debug/` to `.gitignore` for future checkpoint work

## Phase 2: Foundational

- [X] T003 Implement `ComfyHttpClient` and report types in `custom_nodes/comfygo_model_registry/workflow_diagnose.py`
- [X] T004 [P] Implement `workflow_cli.py` argparse entry in `custom_nodes/comfygo_model_registry/workflow_cli.py`

## Phase 3: User Story 1 - Diagnose workflow file (P1)

**Goal**: `--workflow PATH` validates and checks deps; emits DiagnoseReport JSON.

- [X] T005 [US1] Implement `load_workflow_file`, `validate_workflow`, `check_dependencies` in `workflow_diagnose.py`
- [X] T006 [US1] Implement `build_diagnose_report` and `remediation` hints in `workflow_diagnose.py`
- [X] T007 [US1] Add pytest mocks in `custom_nodes/comfygo_model_registry/tests/test_workflow_diagnose.py` for validation + missing node/model

## Phase 4: User Story 2 & 3 - History modes (P2)

**Goal**: `--prompt-id` and `--latest-error` merge execution diagnostics.

- [X] T008 [US2] Implement history loaders and `extract_workflow_from_history` in `workflow_diagnose.py`
- [X] T009 [US3] Implement `find_latest_error_prompt_id` in `workflow_diagnose.py`
- [X] T010 [P] [US2] Add history/execution tests in `test_workflow_diagnose.py`

## Phase 5: User Story 4 - Integration (P3)

**Goal**: `comfygo workflow diagnose` discoverable; agents have protocol.

- [X] T011 [US4] Wire `workflow` command in `scripts/comfy-local` (usage + case dispatch)
- [X] T012 [P] [US4] Add workflow debug protocol to `AGENTS.md` and update SPECKIT plan pointer
- [X] T013 [P] [US4] Add CHANGELOG entry under `[Unreleased]`

## Phase 6: Polish

- [X] T014 Run `./scripts/verify-quality.sh` and fix any failures
- [X] T015 Mark all tasks `[X]` in this file after verification passes

## Dependencies

- US1 (T005-T007) before US2/US3 (T008-T010)
- T003-T004 before US1
- US1-US3 before US4 wiring (T011)

## MVP Scope

T001-T007 + T011 = minimal shippable: file diagnose + comfygo entry point.
