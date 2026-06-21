# Implementation Plan: GC Doctor - guided comfygo operations

**Branch**: `003-gc-doctor` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-gc-doctor/spec.md`

## Summary

Extend the existing `comfygo doctor` entry point into a guided readiness flow
for the full comfygo operation catalog. The command remains read-only by
default: it checks configuration, sync/patch readiness, model-view reconcile
readiness, GC safety readiness, launch/restart readiness, install/update
readiness, and upstream-refresh readiness. It prints every action as
available, blocked, or not relevant, then highlights exactly one recommended
next action using the safety-first order from the spec.

Real changes are run only through the same entry point with explicit user
confirmation or an explicit apply/fix flag. GC apply validation scenarios use
temp roots only; the real model root is inspected by dry-run smoke checks by
default. A live targeted GC action is allowed only through
`doctor --apply targeted-gc --gc-target <name>` after all 16 GCD scenarios pass
and the target is validated.

## Technical Context

**Language/Version**: Bash for the `scripts/comfy-local` / `scripts/comfygo`
entry point; Python 3.11+ only through existing pytest and registry CLI calls.

**Primary Dependencies**:
- Existing wrapper: `scripts/comfygo` delegates to `scripts/comfy-local`
- Existing doctor/status logic in `scripts/comfy-local`
- Existing model wrapper: `scripts/comfygo-models.sh`
- Existing live validator: `scripts/comfygo-live-validate`
- Existing GC matrix: `specs/002-model-gc/doctor-matrix.md`
- Existing test suite under `custom_nodes/comfygo_model_registry/tests`

**Storage**: Filesystem checks over this repo, ComfyUI runtime paths, model
root, generated `.comfygo_views/`, and temp GC doctor roots.

**Testing**: `pytest` through `uv run`; shell syntax checks with `bash -n`;
direct wrapper smoke tests for action inventory and explicit apply/fix gates.

**Target Platform**: Linux/POSIX shell environment.

**Project Type**: CLI workflow in existing repo scripts; no new package.

**Performance Goals**:
- Default readiness inventory completes in under 30 seconds when live runtime
  checks are local and no long-running install/update action is requested.
- GC doctor temp-root scenarios complete in under 30 seconds.

**Constraints**:
- Default `comfygo doctor` remains read-only.
- Real mutating actions require explicit confirmation or an explicit apply/fix
  flag naming the selected action.
- GC apply scenarios run only in temp roots.
- Live model-root GC checks are dry-run only and must not create or modify
  `.comfygo_trash/` during readiness. Live targeted GC mutation requires the
  separate `--apply targeted-gc --gc-target <name>` path.
- Launch/restart actions must not hide prerequisite sync, install, patch, or
  reconcile mutations behind a single confirmation.
- All Python/comfy-cli execution uses uv-first command forms.
- No model weights, tokens, runtime histories, logs, or local prompts are
  committed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Vendored source of truth**: The guided flow extends scripts and registry
  code in this repo first. Live runtime paths remain output targets.
- **Explicit upstream refresh only**: Upstream refresh is listed as an action
  but is recommended only when explicitly requested or clearly blocking
  progress; it is never silently run by readiness checks.
- **Safe daily operation**: The default entry point is diagnostic. Mutating
  actions need confirmation or explicit apply/fix flags. GC live roots remain
  read-only.
- **Patch durability**: Patch status is evaluated from patch files already
  stored in this repo. Patch application remains explicit.
- **Public repo and secret safety**: The feature uses environment variables and
  temp evidence directories; no tokens or machine-local paths are embedded in
  tracked docs or scripts.
- **uv first, direnv for local env**: All Python/comfy-cli operations use
  `uv run`; local env is loaded through the existing wrapper behavior.
- **Verifiable sync and restart behavior**: The feature improves verifiability
  by making readiness state, blocked actions, recommended next action, and
  evidence paths explicit.

**Gate verdict**: PASS - no constitution violations.

## Project Structure

### Documentation (this feature)

```text
specs/003-gc-doctor/
├── plan.md              # This file
├── research.md          # Phase 0 decisions
├── data-model.md        # Phase 1 entities
├── contracts/README.md  # CLI/user-facing contract
├── quickstart.md        # Validation guide
└── spec.md              # Feature specification
```

### Source Code (repository root)

```text
scripts/
├── comfygo               # Existing entry wrapper
├── comfy-local           # Extend doctor workflow here
├── comfygo-models.sh     # Existing model registry wrapper
└── comfygo-live-validate # Existing live validation pattern/evidence style

custom_nodes/comfygo_model_registry/tests/
├── test_doctor.py        # Extend guided readiness/action output tests
├── test_wrapper.py       # Existing wrapper coverage, add GC doctor if needed
└── test_gc.py            # Existing GC safety coverage
```

**Structure Decision**: Extend `scripts/comfy-local doctor` rather than adding
a separate top-level command. This preserves a single `comfygo` entry point and
keeps default doctor behavior diagnostic.

## Phase 0 Research Summary

See [research.md](research.md). Key decisions:

- Use `comfygo doctor` as the single default readiness command.
- Add an action inventory with `available`, `blocked`, and `not relevant`
  statuses.
- Select exactly one recommended next action using the safety-first order.
- Allow real changes only by explicit confirmation or an explicit apply/fix
  flag naming an available action.
- Keep GC real-root checks dry-run only; run GCD apply tests only in temp roots.
- Keep live targeted GC separate from the GCD harness: require `--gc-target`,
  all 16 GCD scenarios passing, and confirmation before delegating to GC apply.

## Phase 1 Design Summary

See [data-model.md](data-model.md) for the action inventory, readiness probes,
GC scenario results, evidence records, and recommendation model.

See [contracts/README.md](contracts/README.md) for CLI contract details.

See [quickstart.md](quickstart.md) for validation scenarios.

## Post-Design Constitution Re-Check

- The design keeps readiness checks read-only by default.
- Mutating actions remain explicit and named.
- Upstream refresh remains explicit or blocking-only.
- GC live-root safety is preserved by keeping readiness dry-run only and
  requiring `--gc-target` plus confirmation for live targeted quarantine.
- uv-first execution is retained.

**Post-design gate verdict**: PASS.
