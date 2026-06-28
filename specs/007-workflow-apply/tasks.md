# Tasks: Workflow Apply CLI

## Phase 1: Core apply

- [X] T001 Implement patch ops and `apply_patches` in `custom_nodes/comfygo_model_registry/workflow_apply.py`
- [X] T002 Implement checkpoint save/list/restore in `workflow_apply.py`
- [X] T003 Add `test_workflow_apply.py` with all four patch ops and checkpoint round-trip

## Phase 2: CLI integration

- [X] T004 Extend `workflow_cli.py` with `apply`, `checkpoint list`, `checkpoint restore`
- [X] T005 Wire `scripts/comfy-local` workflow subcommand dispatch + usage text
- [X] T006 Add `--validate` post-apply using `workflow_diagnose.validate_workflow`

## Phase 3: Docs & polish

- [X] T007 Update `AGENTS.md` workflow protocol (diagnose → apply → validate)
- [X] T008 Add CHANGELOG entry; update `.specify/feature.json`
- [X] T009 Run `./scripts/verify-quality.sh`; mark all tasks `[X]`
