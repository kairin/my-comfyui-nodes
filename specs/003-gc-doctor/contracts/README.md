# Contracts: GC Doctor - guided comfygo operations

## CLI Interface

### `comfygo doctor`

Run readiness checks and print the full action inventory.

**Exit code**:
- `0` when readiness inventory is computed and all required safety probes pass,
  even if some actions are blocked or pending
- `1` when one or more readiness probes fail
- `2` for invalid arguments or refused `--apply` requests

**Required behavior**:
- Performs no real mutation by default.
- Lists every catalog action as `available`, `blocked`, or `not relevant`.
- Prints exactly one recommended next action when any action is available.
- Writes an evidence path when detailed logs are retained.
- Never prompts from the default readiness-only run.
- Does not mark mutating actions available until the GC doctor reports
  `PASS: all 16 GCD scenarios`.

Example output shape:

```text
Comfygo readiness
Evidence: /tmp/comfygo-doctor.XXXXXX

Checks:
  PASS: uv available
  PASS: ComfyUI path configured
  PASS: model registry dry-run
  PASS: GC temp-root doctor
  PASS: live model-root GC dry-run

Actions:
  available  sync              run: scripts/comfygo doctor --apply sync
    delegates to: scripts/comfygo sync
  available  patch-comfyui     run: scripts/comfygo doctor --apply patch-comfyui
    delegates to: scripts/comfygo patch-comfyui
  blocked    reconcile         blocked by patch-comfyui
  blocked    targeted-gc       choose a unique managed folder with --gc-target
  blocked    launch            blocked by sync, patch-comfyui, reconcile
  not relevant update          not requested and not blocking
  not relevant refresh-upstreams not requested and not blocking

Recommended next action:
  patch-comfyui - patches are prerequisite runtime state
  To run: scripts/comfygo doctor --apply patch-comfyui
```

### `comfygo doctor --apply <action-id>`

Run the named action only if the current readiness inventory marks it
`available`.

**Exit code**:
- `0` when the action completes successfully
- `1` when readiness fails or the action fails
- `2` when the action id is unknown, blocked, or not relevant

**Required behavior**:
- Recomputes readiness before applying.
- Refuses blocked or unknown actions.
- Prints the action being run.
- In an interactive TTY, prompts `Run <action-id> now? [y/N]` unless `--yes`
  is present. The default answer is no and exits 2 without mutation.
- In non-interactive mode, requires `--yes`; without it the command exits 2
  without mutation.
- Preserves action-specific safety rules. For example, targeted GC requires
  `--gc-target <name>`, a unique managed target, and all 16 GCD scenarios
  passing. Bulk/no-target live GC apply is forbidden.

### `comfygo doctor --apply targeted-gc --gc-target <name>`

Run a targeted GC quarantine from the same entry point.

**Required behavior**:
- Recomputes readiness and requires `PASS: all 16 GCD scenarios`.
- Requires an explicit model root resolved by configuration or `--models-dir`.
- Refuses missing targets, no matches, multiple matches, symlinked targets,
  ambiguous-only targets, and unsafe target names with exit 2 before mutation.
- Delegates to `scripts/comfygo-models.sh --models-dir <resolved-root> gc -f
  <name> --apply` only after readiness and confirmation checks pass.
- Never runs bulk live GC apply and never runs targeted GC merely because the
  default readiness inventory passed.

### `comfygo doctor --yes --apply <action-id>`

Non-interactive explicit execution for automation. Semantics are the same as
`--apply <action-id>` but no interactive prompt is shown.

### `comfygo doctor --models-dir <path>`

Use an explicit model root for read-only live GC smoke checks and model-view
readiness checks.

**Required behavior**:
- Never runs GC apply against this path.
- Fails if `.comfygo_trash/` is created or modified by a read-only check.
- The doctor-resolved model root is passed to every model-related delegated
  command so recommended commands inspect and mutate the same root.

## Action IDs

| Action ID | Meaning | Mutating? | Recommendation rule |
|-----------|---------|-----------|---------------------|
| `runtime-envrc` | Write machine-local runtime direnv file | Yes | Before sync/patch if runtime env is missing and paths are configured |
| `sync` | Sync vendored custom nodes into ComfyUI | Yes | Before patch/reconcile/launch when runtime copy is missing or stale |
| `patch-comfyui` | Apply ComfyUI core patches | Yes | Before reconcile/launch when patch is not applied |
| `patch-cli` | Apply comfy-cli patch | Yes | Before launch/restart when patch is needed and applicable |
| `reconcile` | Apply model compatibility views | Yes | After sync/patch when reconcile dry-run reports pending changes |
| `targeted-gc` | Quarantine a selected managed folder | Yes | After all 16 GCD scenarios pass and a unique `--gc-target` is selected |
| `launch` | Launch ComfyUI without hidden sync/reconcile/apply work | Yes | After setup/sync/patch/reconcile/GC blockers are clear and prerequisite mutating helpers are no-op |
| `restart` | Restart ComfyUI without hidden sync/reconcile/apply work | Yes | Same readiness as launch, when restart is requested |
| `install` | Run comfy install flow | Yes | Only when explicitly requested or install state blocks launch |
| `update` | Run comfy update flow | Yes | Only when explicitly requested or clearly blocking progress |
| `refresh-upstreams` | Refresh vendored upstream node copies | Yes | Only when explicitly requested |

## Safety Rules

- Default `comfygo doctor` is read-only.
- `--apply` must name exactly one action id.
- `--yes` only suppresses prompts; it does not bypass blocked-action checks.
- Live GC checks are dry-run only.
- Temp-root GC doctor scenarios may use apply against temp roots only.
- Live targeted GC may run only through `doctor --apply targeted-gc --gc-target
  <name>` after all 16 GCD scenarios pass and the target is validated as a
  unique managed non-symlink folder.
- Launch/restart actions must not hide prerequisite mutations. If existing
  launch helpers would sync, install, patch, or reconcile, doctor must either
  use a pure launch/restart path or keep launch/restart blocked until those
  prerequisite actions are already no-op.
- Install/update/upstream refresh are never the recommended next action unless
  explicitly requested or clearly blocking progress.

### `scripts/comfygo-verify`

CI/agent repository verification harness. Separate from `comfygo doctor`.

**Exit code**:
- `0` when all required phases pass
- `1` when any verification phase fails

**Required behavior**:
- Prints an evidence directory path.
- Requires a clean worktree for full verification.
- Runs shell syntax, whitespace, and registry pytest checks.
- Runs the 16-scenario GCD harness in temp roots unless `--fast` is used.
- Runs live validation only when `COMFYUI_DIR` is configured and the
  worktree is clean.
- Does not replace `comfygo doctor`; it is for CI/agent automation, while
  doctor remains the guided readiness and apply surface.
