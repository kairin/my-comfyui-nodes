# Current Issues & Core Work Areas - my-comfyui-nodes GC Doctor

**Date**: 2026-06-28

**Scope**: Current unresolved issues for the `my-comfyui-nodes` model registry,
model GC, `003-gc-doctor` guided operations, and post-merge hygiene.

**Rule for this file**: Only current issues that still require resolution should
be listed here. Resolved review comments, historical debate, and stale external
analysis claims belong in their original feature artifacts, not in this backlog.

## Current Verification Snapshot

These facts were verified against the current checkout on 2026-06-28:

- Shipped (merged PR #106): `specs/006-workflow-diagnose`,
  `specs/007-workflow-apply` — `comfygo workflow diagnose|apply|checkpoint`
- Active Spec Kit feature (documentation pointer):
  `specs/007-workflow-apply`
- Prior feature (complete): `specs/003-gc-doctor`
- `specs/003-gc-doctor/spec.md`: `20` functional requirements and `13`
  success criteria.
- `specs/003-gc-doctor/tasks.md`: `62/62` tasks checked, `0` unchecked.
- `specs/003-gc-doctor/checklists/requirements.md`: `16/16` checked, `0`
  unchecked.
- `specs/003-gc-doctor/checklists/` contains only `requirements.md`.
  `ux-performance.md` and `code-architecture.md` are not present and are not
  required by local tracked artifacts.
- `custom_nodes/comfygo_model_registry/tests/test_wrapper.py` now contains the
  `ManagedDownloader` GCD-016 fixture and
  `test_wrapper_gc_models_dir_before_subcommand_matches_after_subcommand`.
- `specs/003-gc-doctor/quickstart.md` and
  `specs/003-gc-doctor/contracts/README.md` now document
  `scripts/comfygo-verify`.
- Full registry suite:

  ```bash
  UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line -p no:cacheprovider
  ```

  Result: `131 passed` (includes workflow diagnose/apply tests from PR #106).

## Closed Or Non-Blocking Items

These previously tracked items are no longer active issues in this backlog:

| ID | Status | Current reason |
|----|--------|----------------|
| CUR-001 | Verified | Local counts now match expected `20` FRs, `13` SCs, `62/62` tasks, and no unchecked `003-gc-doctor` items. |
| CUR-002 | Confirmed non-blocking | Missing `ux-performance.md` and `code-architecture.md` are stale external references, not local tracked requirements. |
| CUR-003 | Fixed | Wrapper evidence now uses `ManagedDownloader` and includes the before/after `--models-dir` ordering test. |
| CUR-005 | Confirmed non-blocking | The older `001` checklist item is an accepted historical implementation-detail exception and does not block `003-gc-doctor`. |
| CUR-008 | Fixed | `scripts/comfygo-verify` is documented in quickstart and contracts. |
| CUR-009 | Shipped | `006-workflow-diagnose` + `007-workflow-apply` merged in PR #106; see `AGENTS.md` and `docs/workflow.md`. |

Do not reopen these items from a stale Hermes or handoff report. Reopen only if
a fresh local probe contradicts the status above.

## Active Issue Summary

| ID | Severity | Area | Current Issue | Blocking? |
|----|----------|------|---------------|-----------|
| CUR-004 | Low | `002-model-gc` task artifact | T080 is checked but still says `(partial)` | No for `003-gc-doctor`, yes for `002-model-gc` cleanup |
| CUR-006 | Medium | Verification | Dirty worktree (~140 vendored/patch files) prevents clean `scripts/comfygo-verify` | Yes before final signoff |
| CUR-007 | Medium | Live validation | Live runtime read-only validation still needs a clean-tree run | Yes before operational confidence |

## Agent Operating Protocol

1. Verify local state before closing any issue. Do not accept Hermes or another
   agent summary without checking the checkout.
2. Use uv-first commands only. Do not introduce `pip`, `python -m pip`, or
   unwrapped `python` workflow commands.
3. Do not run live mutating operations as part of this backlog. No live
   `gc --apply`, `doctor --apply`, `sync`, `reconcile --apply`, patch, install,
   update, launch, restart, or upstream refresh unless the user separately
   approves that exact action.
4. Do not use destructive git cleanup to force a clean tree. No
   `git reset --hard`, `git clean -fd`, or checkout commands that discard user
   changes unless the user explicitly asks for that operation.
5. Keep `comfygo doctor` and `scripts/comfygo-verify` distinct:
   `comfygo doctor` is the guided user entry point; `scripts/comfygo-verify` is
   the automatable repository validation harness.

## CUR-004 - `002-model-gc` T080 Is Checked But Still Marked Partial

**Severity**: Low

### Current evidence

- `specs/002-model-gc/tasks.md` T080 is checked with `[X]`.
- The same T080 line still ends with `(partial)`.
- Hermes deferred this item to the `002-model-gc` feature context; that is
  acceptable for `003-gc-doctor`, but the artifact contradiction remains.

### Risk

A checked task that says partial creates ambiguity. Either work remains and the
task should not be checked, or the note is stale and should be removed.

### Resolver instructions

1. Confirm current unsafe-name coverage:

   ```bash
   rg -n "validate_path_segment|Unsafe path segment|~UnsafeModel|test_apply_unsafe_source_name_is_controlled_error|test_wrapper_gc_unsafe_source_name_fails_without_traceback" custom_nodes/comfygo_model_registry/gc.py custom_nodes/comfygo_model_registry/models.py custom_nodes/comfygo_model_registry/tests/test_gc.py custom_nodes/comfygo_model_registry/tests/test_cli.py custom_nodes/comfygo_model_registry/tests/test_wrapper.py
   UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests/test_gc.py::test_apply_unsafe_source_name_is_controlled_error custom_nodes/comfygo_model_registry/tests/test_wrapper.py::test_wrapper_gc_unsafe_source_name_fails_without_traceback -q --tb=line -p no:cacheprovider
   ```

2. Expected evidence:

   - `models.validate_path_segment()` enforcement is reached from `gc.py`.
   - `models.py` contains controlled `Unsafe path segment` wording.
   - `test_gc.py` covers direct GC behavior for `~UnsafeModel`.
   - `test_wrapper.py` covers wrapper behavior for `~UnsafeModel`.
   - Focused unsafe-name tests pass.

3. If coverage passes, edit only T080 in `specs/002-model-gc/tasks.md`:

   - Remove trailing `(partial)`.
   - Keep the checkbox checked.
   - Optionally append evidence text naming
     `test_apply_unsafe_source_name_is_controlled_error` and
     `test_wrapper_gc_unsafe_source_name_fails_without_traceback`.

4. If coverage fails:

   - Do not remove `(partial)`.
   - Reopen T080 by unchecking it only if the failure is a real coverage gap.
   - Add the missing direct GC or wrapper coverage before closing it again.

5. Do not add a new `test_cli.py` unsafe-name test unless project policy now
   requires both CLI and wrapper coverage. T080 says `test_cli.py` or
   `test_wrapper.py`, and wrapper coverage satisfies the user-facing shell path.

### Acceptance checks

```bash
rg -n "T080|\(partial\)|Unsafe path segment|~UnsafeModel" specs/002-model-gc/tasks.md custom_nodes/comfygo_model_registry/tests custom_nodes/comfygo_model_registry/gc.py custom_nodes/comfygo_model_registry/models.py
UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests/test_gc.py::test_apply_unsafe_source_name_is_controlled_error custom_nodes/comfygo_model_registry/tests/test_wrapper.py::test_wrapper_gc_unsafe_source_name_fails_without_traceback -q --tb=line -p no:cacheprovider
```

Expected closure state:

- T080 is either clearly complete with no `(partial)` wording, or it is
  explicitly reopened with the missing coverage described.

## CUR-006 - Dirty Worktree Blocks Clean Verification

**Severity**: Medium

### Current evidence

`git status --short --untracked-files=all` still reports modified and untracked
files across the feature implementation. Until the tree is clean,
`scripts/comfygo-verify` will fail its Phase 1 dirty-git preflight.

### Risk

The repository cannot claim a clean verifier pass while the worktree is dirty.
This is expected verifier behavior, not a verifier bug.

### Resolver instructions

1. Finish or intentionally defer CUR-004.
2. Review the current diff and confirm all intended feature files are ready.
3. Stage and commit the feature changes, or otherwise return the worktree to a
   legitimate clean state without discarding user work.
4. Run the clean-tree verifier from a clean checkout:

   ```bash
   git status --short --untracked-files=all
   bash -n scripts/comfygo-verify
   bash -n scripts/comfygo-live-validate
   bash -n scripts/comfy-local
   bash -n scripts/comfygo-models.sh
   git diff --check
   UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line -p no:cacheprovider
   env -u COMFYUI_DIR -u COMFY_CLI_DIR -u COMFY_MODELS_DIR UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 scripts/comfygo-verify
   ```

### Expected closure state

- `git status --short --untracked-files=all` is empty before the final verifier
  run.
- Shell syntax checks exit `0`.
- `git diff --check` exits `0`.
- Full registry suite passes.
- `scripts/comfygo-verify` exits `0` with live env vars unset.
- Final verifier Phase 1, Phase 2, and Phase 3 pass; Phase 4 is skipped when
  live env vars are intentionally unset.
- The verifier prints an `Evidence: /tmp/comfygo-verify.*` directory.

### What not to run

- Do not use `scripts/comfygo-verify --fast` as final signoff; it skips GC
  doctor and live validation.
- Do not run final `scripts/comfygo-verify` with `COMFYUI_DIR` inherited unless
  live runtime sync side effects are explicitly allowed.
- Do not use destructive git cleanup to manufacture a clean tree.

## CUR-007 - Live Runtime Read-Only Validation Needs A Fresh Clean-Tree Run

**Severity**: Medium

### Current evidence

- Full `scripts/comfygo-verify` has not completed live Phase 4 from a clean
  tree after the latest changes.
- `scripts/comfygo-live-validate` currently runs `scripts/comfygo sync`, so it
  is not the strict read-only live validation command.

### Risk

Temp-root safety is covered by tests and the GC doctor harness, but the live
configured model root has not been rechecked in the latest state. The live check
must remain read-only unless the user approves a separate apply/sync operation.

### Resolver instructions

Run only after CUR-006 is green from a clean tree. This sequence validates the
live runtime and live model root without applying GC, reconcile, sync, patch,
launch, restart, install, update, or upstream refresh actions.

```bash
: "${COMFYUI_DIR:?set COMFYUI_DIR to the live ComfyUI checkout first}"

run_id="$(date -u +%Y%m%dT%H%M%SZ)"
evidence="/tmp/comfygo-cur007-$run_id"
mkdir -p "$evidence"

model_root="${COMFY_MODELS_DIR:-}"
if [ -z "$model_root" ]; then
  if [ -d "$COMFYUI_DIR/../models" ]; then
    model_root="$(cd "$COMFYUI_DIR/../models" && pwd)"
  else
    model_root="$COMFYUI_DIR/models"
  fi
fi

test -d "$COMFYUI_DIR"
test -d "$model_root"
git status --short --untracked-files=all | tee "$evidence/git-status-before.log"
test ! -s "$evidence/git-status-before.log"

if [ -e "$model_root/.comfygo_trash" ]; then
  find "$model_root/.comfygo_trash" -mindepth 1 -maxdepth 4 -printf '%y\t%P\t%l\n' | LC_ALL=C sort > "$evidence/trash-before.txt"
else
  printf '__missing__\n' > "$evidence/trash-before.txt"
fi

doctor_rc=0
COMFY_MODELS_DIR="$model_root" UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 scripts/comfygo doctor > "$evidence/doctor-live-readonly.log" 2>&1 || doctor_rc=$?
printf '%s\n' "$doctor_rc" > "$evidence/doctor.rc"

gc_rc=0
UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 scripts/comfygo-models.sh --models-dir "$model_root" gc > "$evidence/live-gc-dry-run.log" 2>&1 || gc_rc=$?
printf '%s\n' "$gc_rc" > "$evidence/gc.rc"

if [ -e "$model_root/.comfygo_trash" ]; then
  find "$model_root/.comfygo_trash" -mindepth 1 -maxdepth 4 -printf '%y\t%P\t%l\n' | LC_ALL=C sort > "$evidence/trash-after.txt"
else
  printf '__missing__\n' > "$evidence/trash-after.txt"
fi

cmp -s "$evidence/trash-before.txt" "$evidence/trash-after.txt"
git status --short --untracked-files=all | tee "$evidence/git-status-after.log"
test ! -s "$evidence/git-status-after.log"
git diff-index --quiet HEAD --
```

### Expected closure state

- The repo is clean before and after the live read-only run.
- `doctor.rc` is `0` when runtime readiness is healthy; if non-zero, inspect
  `doctor-live-readonly.log` and keep CUR-007 open.
- `gc.rc` is `0`.
- `live-gc-dry-run.log` contains dry-run report output only.
- `.comfygo_trash` snapshot before and after is byte-identical.
- Reserved category folders such as `diffusion_models`, `loras`, `vae`,
  `text_encoders`, and `checkpoints` are not reported as ambiguous live GC
  targets.
- Evidence is retained under `/tmp/comfygo-cur007-*`.

### What not to run

- Do not run `scripts/comfygo-live-validate` for strict read-only validation;
  the current script runs `scripts/comfygo sync`.
- Do not run `COMFYUI_DIR=... scripts/comfygo-verify` for strict read-only
  validation unless the live validator has been changed or sync side effects
  are explicitly accepted.
- Do not run `scripts/comfygo-models.sh --models-dir "$model_root" gc --apply`.
- Do not run
  `scripts/comfygo-models.sh --models-dir "$model_root" gc -f NAME --apply`.
- Do not run `scripts/comfygo models reconcile --apply`,
  `scripts/comfygo doctor --apply ...`, `scripts/comfygo sync`,
  `scripts/comfygo patch-*`, `scripts/comfygo launch`,
  `scripts/comfygo restart`, `scripts/comfygo install`,
  `scripts/comfygo update`, or `scripts/comfygo refresh-upstreams`.

## Final Signoff Checklist

Run these before claiming the GC doctor/model registry work is complete:

```bash
rg -n "^- \[ \]" specs/003-gc-doctor/checklists specs/003-gc-doctor/tasks.md
rg -n "\(partial\)" specs/002-model-gc/tasks.md specs/003-gc-doctor/tasks.md
rg -n "test_wrapper_gc_models_dir_after_subcommand_dry_run|test_wrapper_gc_models_dir_before_subcommand_matches_after_subcommand|ManagedDownloader" custom_nodes/comfygo_model_registry/tests/test_wrapper.py
bash -n scripts/comfygo-verify
bash -n scripts/comfygo-live-validate
bash -n scripts/comfygo-models.sh
bash -n scripts/comfy-local
git diff --check
UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line -p no:cacheprovider
git status --short --untracked-files=all
env -u COMFYUI_DIR -u COMFY_CLI_DIR -u COMFY_MODELS_DIR UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 scripts/comfygo-verify
```

The last verifier command must be run from a clean worktree. If live runtime
validation is required, use the CUR-007 read-only live validation runbook unless
sync side effects are explicitly accepted.
