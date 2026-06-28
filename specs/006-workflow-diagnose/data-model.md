# Data Model: Workflow Diagnose CLI

## DiagnoseReport (stdout JSON)

| Field | Type | Description |
|-------|------|-------------|
| `source` | object | How workflow was loaded |
| `source.type` | string | `workflow_file` \| `prompt_id` \| `latest_error` |
| `source.path` | string? | File path when type is workflow_file |
| `source.prompt_id` | string? | When from history |
| `source.host` | string | ComfyUI base URL used |
| `workflow_summary` | object | `node_count`, `class_types[]` |
| `validation` | object | `ok: bool`, `node_errors`, `error` |
| `dependencies` | object | `missing_nodes[]`, `missing_models[]`, `skipped_reason?` |
| `execution` | object? | Present when history sourced; status, messages, errors |
| `remediation` | array | Ordered hints with `kind`, `message`, `command?` |

## WorkflowSource

One of three mutually exclusive modes per invocation (FR-002).

## RemediationHint

| Field | Description |
|-------|-------------|
| `kind` | `install_node`, `missing_model`, `validation_error`, `execution_error` |
| `message` | Human-readable summary |
| `command` | Optional shell command (`comfy node install ...`) |
| `node_id` | Optional affected node |
| `parameter` | Optional widget name |

## HistoryEntry (from ComfyUI API)

Read-only view: `status`, `messages`, `prompt` tuple where index 2 is API workflow dict.
