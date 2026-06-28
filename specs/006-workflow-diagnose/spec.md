# Feature Specification: Workflow Diagnose CLI

**Feature Branch**: `006-workflow-diagnose`

**Created**: 2026-06-28

**Status**: Draft

**Input**: User description: "CLI workflow diagnose for agent review — validate ComfyUI workflows via comfygo, capture errors from workflow JSON or prompt_id, check dependencies, emit structured JSON report for coding agents to review and fix workflows outside the browser."

## Clarifications

### Session 2026-06-28

- Primary user is a solo maintainer over SSH with ComfyUI in tmux and a coding agent (Cursor/Grok) in a separate terminal.
- Diagnose is **read-only** toward the ComfyUI canvas: it does not auto-apply fixes in v1.
- The single entry point remains `comfygo`; new surface is `comfygo workflow diagnose`.
- Workflow input is ComfyUI **API format** JSON (execution prompt), not LiteGraph UI format.
- Local ComfyUI server is the default target; cloud is out of scope for v1.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Diagnose a Saved Workflow File (Priority: P1)

A maintainer exports or saves a broken workflow as API JSON. They run one command and receive a structured report listing validation errors, missing nodes/models, and suggested remediation commands — without opening ComfyUI Copilot or manually reading server logs.

**Why this priority**: Covers pre-queue validation failures (red nodes, bad parameters, missing wires) where no `prompt_id` exists yet.

**Independent Test**: Run `comfygo workflow diagnose --workflow broken.json` against a running ComfyUI instance with mocked or fixture workflow; report contains `validation` and `dependencies` sections.

**Acceptance Scenarios**:

1. **Given** a running ComfyUI server and a workflow JSON file with an invalid parameter, **When** the user runs `comfygo workflow diagnose --workflow path.json`, **Then** stdout is a JSON object with `validation.ok: false` and per-node error details.
2. **Given** a workflow referencing a custom node not installed on the server, **When** diagnose runs, **Then** the report lists the missing `class_type` and a suggested `comfy node install` command when known.
3. **Given** a workflow referencing a checkpoint not on disk, **When** diagnose runs, **Then** the report lists the missing model with node id and parameter name.

---

### User Story 2 - Diagnose a Failed Run by prompt_id (Priority: P2)

After queueing a workflow that fails at runtime, the maintainer copies the `prompt_id` from ComfyUI or history. They run diagnose with that id; the tool loads the exact prompt from server history and merges validation, dependency, and execution traceback into one report.

**Why this priority**: Most painful failures happen after queue; history already holds the workflow — no manual export.

**Independent Test**: `comfygo workflow diagnose --prompt-id <id>` returns `execution` section with error status when history entry is an error.

**Acceptance Scenarios**:

1. **Given** a completed error entry in ComfyUI history, **When** the user runs `comfygo workflow diagnose --prompt-id ID`, **Then** the report includes `execution.status_str: error` and extracted error messages.
2. **Given** a valid prompt_id, **When** diagnose runs, **Then** the embedded workflow is used for validation and dependency checks without requiring `--workflow`.

---

### User Story 3 - Diagnose Latest Error (Priority: P2)

The maintainer does not have the prompt_id handy. They run `comfygo workflow diagnose --latest-error` and the tool finds the most recent failed history entry on the local server.

**Why this priority**: Reduces friction for the common "it just failed" case over SSH.

**Independent Test**: With fixture history containing one error entry, `--latest-error` selects it and produces the same shape report as `--prompt-id`.

**Acceptance Scenarios**:

1. **Given** at least one error in recent ComfyUI history, **When** the user runs `comfygo workflow diagnose --latest-error`, **Then** stdout identifies the chosen `prompt_id` in `source` and includes execution diagnostics.
2. **Given** no error entries in history, **When** `--latest-error` is used, **Then** the command exits non-zero with a clear message (no silent success).

---

### User Story 4 - Agent Review Protocol (Priority: P3)

A coding agent reads `AGENTS.md` and knows how to invoke diagnose, interpret the JSON, propose JSON patches or remediation commands, and ask the user to re-run diagnose after fixes.

**Why this priority**: Makes the feature usable by agents without bespoke instructions each session.

**Independent Test**: `AGENTS.md` contains a workflow debug protocol section referencing `comfygo workflow diagnose`.

**Acceptance Scenarios**:

1. **Given** an agent with repo context, **When** the user reports a workflow failure, **Then** the agent can run diagnose commands and explain errors using fields from the report schema.

---

### Edge Cases

- ComfyUI server not running: clear error, non-zero exit, no partial JSON claiming success.
- Invalid workflow JSON file: parse error before any HTTP call.
- `prompt_id` not found in history: clear error naming the id.
- Empty workflow (no nodes): validation fails with explicit reason.
- `/object_info` temporarily unavailable: dependency check marked `skipped` with reason, not false "all ok".
- Multiple simultaneous errors: report lists all `node_errors`, not only the first.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `comfygo workflow diagnose` MUST be reachable from the single `comfygo` entry point.
- **FR-002**: The command MUST accept exactly one workflow source mode per invocation: `--workflow PATH`, `--prompt-id ID`, or `--latest-error`.
- **FR-003**: The command MUST POST the workflow to the running ComfyUI server's prompt validation path and include parsed `node_errors` in the report when validation fails.
- **FR-004**: The command MUST compare required `class_type` values against live `object_info` and report missing custom nodes with install hints when mapped.
- **FR-005**: The command MUST compare model-loader parameters against live model folder listings for common loader types and report missing models.
- **FR-006**: When sourced from history (`--prompt-id` or `--latest-error`), the command MUST include execution status and error messages/tracebacks from the history entry.
- **FR-007**: The command MUST emit a single JSON document on stdout suitable for agent consumption; human-oriented hints MAY go to stderr.
- **FR-008**: The command MUST default to `http://127.0.0.1:8188` and allow `--host URL` override without requiring secrets in committed files.
- **FR-009**: Implementation MUST be uv-first (`uv run --no-project python ...`) consistent with other `comfygo` Python helpers.
- **FR-010**: The feature MUST include automated tests with mocked HTTP responses (no live ComfyUI required in CI).

### Repository Policy Requirements

- No tokens, API keys, or machine-local paths in committed artifacts.
- Read-only toward ComfyUI: no queue execution, no canvas mutation, no automatic model downloads in v1.
- Preserve existing speckit features and `comfygo` subcommands.

### Key Entities

- **DiagnoseReport**: Structured JSON output with `source`, `workflow_summary`, `validation`, `dependencies`, `execution` (optional), and `remediation` sections.
- **WorkflowSource**: How the API-format workflow was obtained (file path, prompt_id, or latest-error).
- **RemediationHint**: Actionable suggestion (`install_node`, `download_model`, `fix_parameter`, `fix_connection`) with optional shell command string.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer can obtain a full structured error report in one command without using the ComfyUI browser UI.
- **SC-002**: For a fixture workflow with known validation errors, pytest proves the report contains the expected node ids and error types.
- **SC-003**: `comfygo workflow diagnose --help` is documented in `comfygo` usage output and discoverable from `comfygo --help` flow.
- **SC-004**: An agent following `AGENTS.md` can diagnose by `prompt_id` or workflow file and propose fixes without Copilot installed.

## Assumptions

- Local ComfyUI listens on 127.0.0.1:8188 unless overridden.
- Users can save/export API-format workflow JSON from ComfyUI when pre-queue diagnosis is needed.
- v1 does not include `workflow apply` or checkpoint restore (future feature).
- Model folder checks use ComfyUI HTTP `/models/{folder}` listings, not direct filesystem scan (server is source of truth for what ComfyUI sees).

## Open Questions

None — scope and defaults are sufficient for v1.
