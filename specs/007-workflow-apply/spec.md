# Feature Specification: Workflow Apply CLI

**Feature Branch**: `007-workflow-apply`

**Created**: 2026-06-28

**Status**: Draft

**Input**: Apply JSON patches to ComfyUI API workflows with checkpoints, validate via diagnose, output fixed workflow for ComfyUI load. Follow-on to 006-workflow-diagnose.

## Clarifications

### Session 2026-06-28

- v1 applies patches to **files on disk** and writes a new workflow JSON; it does not push to the browser canvas (no ComfyUI extension).
- Checkpoints live under gitignored `.comfygo_debug/checkpoints/`.
- `--validate` optionally runs live ComfyUI validation after apply (reuses diagnose logic).
- Builds on `comfygo workflow diagnose` from feature 006.

## User Story 1 - Apply Patches to Workflow File (P1)

A maintainer or agent has a broken workflow JSON and a patch list. One command applies patches, saves a checkpoint of the original, writes the fixed file, and reports what changed.

**Independent Test**: Apply `set_input` patch to fixture workflow; output file has updated value; checkpoint exists.

**Acceptance Scenarios**:

1. **Given** a workflow file and patch file, **When** `comfygo workflow apply --workflow W --patch P --output O`, **Then** `O` contains patched workflow and a checkpoint of `W` is saved.
2. **Given** invalid patch JSON, **When** apply runs, **Then** non-zero exit and original workflow unchanged except checkpoint of pre-apply state.

## User Story 2 - Checkpoint Restore (P2)

Before applying risky patches, user can list and restore prior workflow snapshots to a file.

**Acceptance Scenarios**:

1. **Given** existing checkpoints, **When** `comfygo workflow checkpoint list`, **Then** stdout lists checkpoint ids with timestamps and source paths.
2. **Given** a checkpoint id, **When** `comfygo workflow checkpoint restore --id ID --output R`, **Then** `R` contains the saved workflow JSON.

## User Story 3 - Post-Apply Validation (P2)

After apply, optionally validate against live ComfyUI without a separate diagnose invocation.

**Acceptance Scenarios**:

1. **Given** `--validate` and running ComfyUI, **When** apply completes, **Then** validation section is printed to stderr or embedded in result JSON and exit code reflects validation outcome.

## User Story 4 - Agent Protocol Update (P3)

`AGENTS.md` documents apply + checkpoint flow after diagnose.

## Functional Requirements

- **FR-001**: `comfygo workflow apply` reachable from `comfygo` entry point.
- **FR-002**: Supported patch ops: `set_input`, `connect`, `add_node`, `remove_node`.
- **FR-003**: Apply MUST save a checkpoint of the input workflow before mutation.
- **FR-004**: Apply MUST write output workflow (default: `<stem>.applied.json` beside input).
- **FR-005**: `comfygo workflow checkpoint list` and `checkpoint restore` MUST manage `.comfygo_debug/checkpoints/`.
- **FR-006**: `--validate` MUST reuse diagnose validation against `--host` (default 127.0.0.1:8188).
- **FR-007**: uv-first Python; pytest with no live ComfyUI in CI.
- **FR-008**: Read-only toward ComfyUI server except validation POST (same as diagnose).

## Out of Scope (v1)

- Browser canvas auto-load
- LLM-generated patches (agent produces patch JSON externally)
- SQLite session store

## Success Criteria

- **SC-001**: Agent can diagnose → apply patches → re-validate in three commands.
- **SC-002**: pytest covers all four patch ops and checkpoint round-trip.
- **SC-003**: Failed patch does not corrupt checkpoint store.

## Assumptions

- Patches are a JSON array of operation objects.
- Workflow format is ComfyUI API prompt dict (same as 006).
