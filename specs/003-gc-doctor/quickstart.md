# Quickstart: GC Doctor - guided comfygo operations

**Validation guide** for the guided comfygo readiness flow.

## Prerequisites

- `uv` installed
- Feature 001 model registry present
- Feature 002 GC command present
- Optional: `COMFYUI_DIR` and `COMFY_CLI_DIR` configured for live runtime checks

## Scenario 1: Readiness Inventory

Run the default guided doctor:

```bash
scripts/comfygo doctor
```

Expected:

- exits 0 if all required readiness probes pass
- performs no real runtime or model-root mutation
- lists every action as available, blocked, or not relevant
- prints exactly one recommended next action when any action is available
- runs GC doctor temp-root checks
- marks mutating actions available only after `PASS: all 16 GCD scenarios`
- runs live model-root GC dry-run only when a model root is configured

## Scenario 2: Explicit Model Root Smoke

Run readiness with an explicit model root:

```bash
scripts/comfygo doctor --models-dir "$COMFYUI_MODELS_DIR"
```

Expected:

- live GC smoke uses dry-run only
- `.comfygo_trash/` is not created if absent
- existing `.comfygo_trash/` is not modified
- reserved ComfyUI category folders are not reported as ambiguous
- all model-related recommended commands use the same resolved model root

## Scenario 3: Apply A Recommended Action

After `comfygo doctor` reports an available action:

```bash
scripts/comfygo doctor --apply sync
```

Expected:

- doctor recomputes readiness first
- action runs only if `sync` is still available
- blocked or unknown actions are refused
- mutating action is named in output
- on an interactive TTY, the command prompts `Run sync now? [y/N]`
- in non-interactive mode without `--yes`, the command exits 2 without mutation

For non-interactive automation:

```bash
scripts/comfygo doctor --yes --apply sync
```

## Scenario 4: Targeted GC From The Same Entry Point

After `comfygo doctor` reports `targeted-gc` as available for a selected
managed folder:

```bash
scripts/comfygo doctor --models-dir "$COMFYUI_MODELS_DIR" \
  --apply targeted-gc --gc-target ManagedDownloader
```

Expected:

- doctor recomputes readiness first
- all 16 GCD scenarios must pass before live targeted GC can proceed
- missing `--gc-target`, no match, multiple matches, ambiguous-only match,
  symlink target, and unsafe target names exit 2 without mutation
- bulk/no-target live GC apply is never run
- on an interactive TTY, the command prompts before mutation
- for non-interactive automation, use `--yes`

## Scenario 5: Blocked Action Refusal

Try applying an action that the inventory reports as blocked:

```bash
scripts/comfygo doctor --apply launch
```

Expected:

- exits 2
- prints the blocker, such as missing sync, unapplied patch, pending reconcile,
  or missing configuration
- does not launch ComfyUI
- does not run hidden sync, install, patch, or reconcile work behind launch

Unknown and not-relevant actions also exit 2:

```bash
scripts/comfygo doctor --yes --apply definitely-not-real
scripts/comfygo doctor --yes --apply refresh-upstreams
```

## Scenario 6: GC Matrix Validation

Run the focused registry tests:

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 \
  uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line \
  -p no:cacheprovider
```

Expected:

- all registry and GC tests pass
- wrapper flag-order tests pass
- GC dry-run and apply safety tests use temp roots only

Run a timed GC doctor pass against local temp roots:

```bash
scripts/comfygo doctor --keep-evidence
```

Expected:

- all 16 GCD scenarios complete in under 30 seconds
- success removes the temporary model root unless `--keep-evidence` is present
- failure retains and prints the temp root and evidence paths

## Scenario 7: Shell And Whitespace Checks

```bash
bash -n scripts/comfy-local
bash -n scripts/comfygo-models.sh
git diff --check
```

### Scenario 8: CI-Style Repository Verification

Use `scripts/comfygo-verify` when an agent or CI job needs one automatable
repository validation command. This is separate from `scripts/comfygo doctor`:
doctor is the guided user-facing readiness and apply entry point; the verifier
is the repo validation harness.

```bash
UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-verify
```

Expected:
- prints an `Evidence: /tmp/comfygo-verify.*` directory
- fails if `git status --porcelain` is dirty
- runs shell syntax checks and `git diff --check`
- runs the registry pytest suite through `uv run`
- runs all 16 GCD scenarios in isolated temp roots
- runs live validation only when `COMFYUI_DIR` points to a valid runtime
  checkout and the worktree is clean
- exits `0` only when all required phases pass

For a faster local loop:

```bash
UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-verify --fast
```

Expected:
- runs pre-flight and repository tests
- skips the GC doctor and live validation phases

Expected: all commands pass.
