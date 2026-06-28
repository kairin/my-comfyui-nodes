# Implementation Plan: Workflow Diagnose CLI

**Branch**: `006-workflow-diagnose` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

## Summary

Add `comfygo workflow diagnose` — a read-only CLI that talks to a running local ComfyUI server, validates API-format workflows, checks node/model dependencies, and emits a structured JSON report for coding agents. Supports `--workflow`, `--prompt-id`, and `--latest-error` input modes.

## Technical Context

**Language/Version**: Python 3.11+ (diagnose logic) + Bash (`comfy-local` dispatch). uv-first.

**Primary Dependencies**: stdlib `urllib` for HTTP (no new packages). Running ComfyUI HTTP API on local host.

**Storage**: None persisted in v1 (stdout JSON only). Future checkpoints would use gitignored `.comfygo_debug/`.

**Testing**: pytest with mocked HTTP client in `custom_nodes/comfygo_model_registry/tests/test_workflow_diagnose.py`.

**Target Platform**: Linux server, SSH + tmux ComfyUI (same as 004).

**Constraints**:
- Read-only: no `/prompt` queue side effects beyond validation POST (ComfyUI validates before queueing on error).
- Single entry point: `comfygo workflow diagnose`.
- No secrets in repo; `--host` only.

## Constitution Check

- **uv First**: PASS — `uv run --no-project python -m custom_nodes.comfygo_model_registry.workflow_cli`
- **Vendored source of truth**: PASS — logic lives in owned `comfygo_model_registry` package
- **Safe daily operation**: PASS — read-only diagnose, no hidden mutations
- **Public repo / secret safety**: PASS — no tokens in code or specs
- **Verifiable behavior**: PASS — pytest + quickstart scenarios

**Gate verdict**: PASS

## Project Structure

```text
custom_nodes/comfygo_model_registry/
├── workflow_diagnose.py    # Core: HTTP, validate, deps, report builder
├── workflow_cli.py         # argparse entry for diagnose subcommand
└── tests/
    └── test_workflow_diagnose.py

scripts/comfy-local         # Add `workflow` command dispatch
AGENTS.md                   # Workflow debug protocol for agents
CHANGELOG.md                # User-facing entry
```

## Phases

**Phase 1**: Core `workflow_diagnose.py` + tests (US1 validation + deps)

**Phase 2**: History modes `--prompt-id`, `--latest-error` + execution section (US2/US3)

**Phase 3**: `comfygo` wiring, usage text, AGENTS.md protocol (US4)

**Phase 4**: verify-quality.sh, mark tasks complete

## Key Implementation Notes

- Inject `ComfyHttpClient` protocol for tests.
- `extract_workflow_from_history`: `entry["prompt"][2]` when prompt is list/tuple.
- `validate_workflow`: POST `{"prompt": workflow, "client_id": "comfygo_diagnose"}` — parse `node_errors`, `error`.
- Model loaders: focused `MODEL_LOADERS` map (checkpoints, vae, lora, unet, clip) aligned with vendored stack.
- `NODE_TO_PACKAGE` hints for nodes in `UPSTREAMS.tsv` plus common community nodes.
- Exit code 0 when `validation.ok` and no execution error; non-zero otherwise.

## Verification Approach

- pytest mocked HTTP (no live server in CI)
- quickstart.md manual scenario against local ComfyUI when available
- `./scripts/verify-quality.sh` before commit
