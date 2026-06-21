# Data Model: GC Doctor - guided comfygo operations

## Entities

### ActionCatalog

The fixed set of comfygo actions evaluated by the guided readiness flow.

| Field | Type | Description |
|-------|------|-------------|
| actions | list[ActionStatus] | Sync, patch, reconcile, targeted GC, launch/restart, install/update, upstream refresh |
| recommended | RecommendedNextAction? | Exactly one recommended available action, when any action is available |
| evidence_dir | Path? | Temporary evidence directory for probe logs |

## ActionStatus

Readiness result for one possible real action.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Stable action id such as `sync`, `patch-comfyui`, `reconcile`, `targeted-gc`, `launch`, `update`, `refresh-upstreams` |
| label | str | User-facing action name |
| status | enum | `available`, `blocked`, `not_relevant` |
| reason | str | Why the action has this status |
| command | str? | Exact command/action to run when available |
| mutating | bool | Whether running the action changes real runtime/model state |
| requires_confirmation | bool | True for every mutating action |
| prerequisites | list[str] | Action ids or readiness checks that must pass first |
| target_args | list[str] | Required target flags for actions that need a selected object, such as `--gc-target <name>` for `targeted-gc` |

## RecommendedNextAction

The one highlighted next step chosen from available actions.

| Field | Type | Description |
|-------|------|-------------|
| action_id | str | References an ActionStatus id |
| rationale | str | Dependency/safety reason for choosing it |
| command | str | Exact command/action to run |
| confirmation_mode | enum | `prompt` or `explicit_flag` |

## ReadinessProbe

A diagnostic check that feeds one or more ActionStatus results.

| Field | Type | Description |
|-------|------|-------------|
| id | str | Stable probe id |
| command | str | Command or internal check performed |
| exit_code | int | Probe exit code |
| passed | bool | Whether the probe passed |
| output_path | Path? | Evidence log path |
| observed_state | str | Short summary of what was found |

## GCDScenarioResult

Result for one scenario from `specs/002-model-gc/doctor-matrix.md`.

| Field | Type | Description |
|-------|------|-------------|
| id | str | GCD-001 through GCD-016 |
| expected_exit | int | Expected exit code |
| actual_exit | int | Observed exit code |
| passed | bool | Exit, output, and mutation assertions all passed |
| stdout_path | Path | Captured stdout |
| stderr_path | Path | Captured stderr |
| mutation_result | str | Summary of filesystem mutation assertion |

## EvidenceRecord

A log artifact written during readiness or scenario checks.

| Field | Type | Description |
|-------|------|-------------|
| path | Path | Temporary evidence path |
| label | str | Human-readable purpose |
| retained | bool | Whether the record should be retained after success |

## State Transitions

ActionStatus:

```text
unknown -> available
unknown -> blocked
unknown -> not_relevant
available -> executed (only after confirmation or explicit apply/fix flag)
blocked -> available (after the blocking condition is resolved and doctor reruns)
```

RecommendedNextAction:

```text
none -> selected from available actions
selected -> executed only through confirmation or explicit apply/fix flag
```

## Validation Rules

- A mutating action can never be executed during a default readiness-only run.
- A mutating action requires an available ActionStatus and explicit
  confirmation or an explicit apply/fix flag.
- In non-interactive execution, a mutating action requires `--yes` in addition
  to `--apply <action-id>`.
- Exactly one RecommendedNextAction is emitted when one or more actions are
  available.
- RecommendedNextAction must follow the safety-first order.
- GC live-root probes are read-only and must not modify `.comfygo_trash/`.
- GC apply/idempotency checks are allowed only for temp roots.
- Live `targeted-gc` is never bulk apply. It requires all 16 GCD scenarios to
  pass, an explicit `--gc-target <name>`, and validation that the target is a
  unique managed non-symlink folder.
- `launch` and `restart` can be available only when their prerequisite sync,
  patch, reconcile, and GC actions are already no-op; they must not hide
  additional mutating work behind a single confirmation.
