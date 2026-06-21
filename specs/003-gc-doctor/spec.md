# Feature Specification: GC Doctor — automated safety validation harness

**Feature Branch**: `003-gc-doctor`

**Created**: 2026-06-21

**Status**: Draft

**Input**: User description: "Guided comfygo readiness flow that validates all
16 GCD scenarios from the GC doctor matrix in an isolated temporary model
root, can also inspect the actual configured model root in read-only mode,
and tells the user what safe action can be run next without requiring them to
remember separate commands."

## Clarifications

### Session 2026-06-21

- Q: What scope should the GC doctor have: temp-root-only, optional live dry-run, or a guided single-entry flow? → A: Guided single-entry workflow: both registry and GC readiness checks should be reachable from one comfygo entry point, show whether real changes are safe to run next, and tell the user the next command/action without requiring command memorization.
- Q: Should the guided entry point only recommend actions, ask for confirmation, or auto-run changes after checks pass? → A: Use guided confirmation: identify all possible safe actions first, then when readiness conditions are met, inform the user which actions can proceed and offer to run an action only with explicit confirmation or an explicit apply/fix flag.
- Q: Which action scope should the guided flow identify: GC-only, registry plus GC, or full comfygo operations? → A: Full comfygo operations: identify sync, patch, reconcile, targeted GC, launch/restart, install/update, and upstream refresh actions.
- Q: How should the guided flow present multiple available actions? → A: Use inventory plus recommended next: list every action status, then highlight the next best action based on dependencies and safety.
- Q: What dependency order should choose the recommended next action? → A: Safety-first: recommend setup, sync, and patch before reconcile; reconcile before targeted GC; GC before launch/restart; install, update, and upstream refresh only when explicitly requested or clearly blocking progress.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Guided Readiness And Dry-Run Validation (Priority: P1)

A user wants one place to learn whether comfygo operations are ready and what
they can safely do next. They run the comfygo doctor entry point, which reports
readiness for sync, patch, reconcile, targeted GC, launch/restart,
install/update, and upstream refresh actions. The flow includes GC doctor
readiness by setting up a temp model root with known fixtures (managed
folders, ambiguous folders, source symlinks, reserved names, hidden folders)
and validating each dry-run scenario against expected output.

**Why this priority**: Dry-run safety is the foundation. All 8 dry-run
scenarios (GCD-001 through GCD-008) must pass before any apply-mode testing
is reliable. A guided entry point prevents the user from having to remember
separate diagnostic and action commands for the full comfygo workflow.

**Independent Test**: Run the comfygo doctor entry point with a temp root.
All dry-run scenarios pass. The command exits 0. The evidence directory
contains `PASS:` lines for GCD-001 through GCD-008, and the user-visible
summary includes the next safe action.

**Acceptance Scenarios**:

1. **Given** registry checks and GC doctor checks both pass,
   **When** the user reads the final summary, **Then** it tells them what
   actual change is safe to run next and the exact command/action to use.
2. **Given** multiple safe actions are possible, **When** readiness checks
   finish, **Then** the summary lists every action whose prerequisites are
   satisfied and separates any blocked actions with the reason they cannot
   proceed yet.
3. **Given** the user chooses a listed action, **When** they confirm it or
   rerun with an explicit apply/fix flag, **Then** the same comfygo entry
   point may run that action.
4. **Given** the user does not confirm an action and provides no explicit
   apply/fix flag, **When** readiness checks finish, **Then** no real model
   root or runtime state is modified.
5. **Given** the guided entry point completes its readiness pass, **When**
   it builds the action list, **Then** it considers sync, patch, reconcile,
   targeted GC, launch/restart, install/update, and upstream refresh actions.
6. **Given** more than one action is available, **When** the summary is
   printed, **Then** it lists the status of every action and highlights one
   recommended next action based on dependency order and safety.
7. **Given** multiple actions are available, **When** the guided flow selects
   the recommended next action, **Then** it prioritizes setup, sync, and patch
   before reconcile; reconcile before targeted GC; targeted GC before
   launch/restart; and install, update, or upstream refresh only when those
   actions were explicitly requested or are clearly blocking progress.
8. **Given** the guided flow has not yet validated all 16 GCD scenarios,
   **When** it builds the action list, **Then** no real mutating action is
   marked available; mutating actions remain blocked until the summary includes
   `PASS: all 16 GCD scenarios`.
9. **Given** an empty temp model root, **When** the harness runs `gc`,
   **Then** output matches `Nothing to report.` exactly (GCD-001).
10. **Given** a managed folder with `.comfygo-download.json`,
   **When** the harness runs `gc`, **Then** output contains
   `Managed folders:` and `marker: downloader` (GCD-002).
11. **Given** a managed folder with `comfygo-model.json`,
   **When** the harness runs `gc`, **Then** output contains
   `Managed folders:` and `marker: descriptor` (GCD-003).
12. **Given** an ambiguous folder (no marker), **When** the harness runs
   `gc`, **Then** output contains `Ambiguous:` and
   `no marker file found` (GCD-004).
13. **Given** reserved and hidden folders only, **When** the harness runs
   `gc`, **Then** output matches `Nothing to report.` (GCD-005).
14. **Given** a source symlink to a managed folder, **When** the harness
   runs `gc`, **Then** output contains a symlink warning (GCD-006).
15. **Given** a source symlink with `-f` filter, **When** the harness runs
   `gc -f LinkedModel`, **Then** exit 1 (GCD-007).
16. **Given** a source symlink with `-f --apply`, **When** the harness
   runs `gc -f LinkedModel --apply`, **Then** exit 1, no mutation
   (GCD-008).

---

### User Story 2 - Error Gate Validation (Priority: P1)

The harness validates that all safety gates reject invalid or ambiguous
commands without modifying any files. These scenarios verify the "fail
closed" behavior.

**Why this priority**: Error gates are the second safety layer after
dry-run. If any gate silently passes, model folders could be moved
accidentally.

**Independent Test**: Run the harness with fixture folders. All 5 error
gate scenarios (GCD-009 through GCD-013) pass. The source folders remain
unchanged after each test. No `.comfygo_trash/` is created by error gate
scenarios.

**Acceptance Scenarios**:

1. **Given** a managed folder, **When** running `gc --apply` without `-f`,
   **Then** harness asserts error "error: --apply requires -f NAME" and
   exit 1 (GCD-009).
2. **Given** a managed folder, **When** running `gc -f Missing --apply`,
   **Then** harness asserts error "No managed folder matching" and exit 1
   (GCD-010).
3. **Given** an ambiguous folder, **When** running
   `gc -f AmbiguousOnly --apply`, **Then** harness asserts "not managed
   by comfygo" and exit 1 (GCD-011).
4. **Given** two managed folders matching a filter, **When** running
   `gc -f Model --apply`, **Then** harness asserts "multiple managed
   folders" and exit 1 (GCD-012).
5. **Given** a folder with an unsafe path segment name, **When** running
   `gc -f ~UnsafeModel --apply`, **Then** harness asserts an unsafe path
   error, exit 1, no traceback (GCD-013).

---

### User Story 3 - Apply And Idempotency Validation (Priority: P2)

The harness validates that the quarantine apply works correctly and that
re-applying on an already-quarantined folder is safe.

**Why this priority**: Apply mode is the most dangerous operation GC can
perform. These scenarios prove it moves only the correct folder and that
the system is idempotent.

**Independent Test**: Run the harness. GCD-014 succeeds (folder
quarantined to `.comfygo_trash/<date>/`). GCD-015 succeeds (second apply
on same name exits 1).

**Acceptance Scenarios**:

1. **Given** a single managed folder, **When** running
   `gc -f ManagedDownloader --apply`, **Then** harness asserts
   `Quarantined:` in output, source folder gone, trash directory created,
   exit 0 (GCD-014).
2. **Given** the quarantine from GCD-014 has occurred, **When** running
   `gc -f ManagedDownloader --apply` again, **Then** harness asserts
   error about "no managed folder matching", exit 1, quarantined folder
   unchanged (GCD-015).

---

### User Story 4 - Flag Ordering Compatibility (Priority: P2)

Users may place `--models-dir` before or after the `gc` subcommand. The
harness validates that both orderings work identically.

**Why this priority**: The existing `reconcile` subcommand supports
flexible flag ordering. GC must maintain the same behavior.

**Acceptance Scenarios**:

1. **Given** a managed folder, **When** running
   `gc --models-dir "$DIR"` (flag after subcommand), **Then** output
   matches the dry-run result from GCD-002 (GCD-016).

---

### Edge Cases

- **Fixture setup failure**: If any fixture folder cannot be created, the
  harness reports a setup error and stops rather than running scenarios
  on a broken root.
- **Temp root pre-exists**: If the temp root path already exists (race),
  the harness fails early with a clear message.
- **Wrapper not found**: If `scripts/comfygo-models.sh` is missing, the
  harness fails with a clear message before creating any fixtures.
- **Evidence directory full**: If the pre-/post-snapshot is too large, the
  harness caps the output or warns.
- **GCD dependency**: GCD-015 depends on GCD-014 having run first. The
  harness MUST run them sequentially in the defined order.
- **Live root invocation**: If a real model root is configured or explicitly
  supplied, the default harness may run read-only GC dry-run smoke checks
  against it. Live targeted GC quarantine is allowed only through the same
  guided entry point with `--apply targeted-gc --gc-target <name>`, after all
  16 GCD scenarios pass, after the target is validated as a unique managed
  non-symlink folder, and after explicit confirmation or `--yes`. Bulk/no-target
  live GC apply remains forbidden.
- **Missing live root**: If no actual model root can be resolved, the harness
  still runs temp-root safety scenarios and reports live-root readiness as
  unknown with the next action needed to provide or configure the model root.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The harness MUST set up a temporary model root with all
  required fixture folders before running any scenarios, and clean it up
  after completion (or leave it for inspection on failure).
- **FR-002**: The harness MUST create fixture folders with exact names
  matching the doctor-matrix.md specification (`ManagedDownloader`,
  `ManagedDescriptor`, `AmbiguousOnly`, `ModelOne`, `ModelTwo`,
  `LinkedModel`, `~UnsafeModel`, `diffusion_models`, `loras`,
  `.hidden_folder`, `.comfygo_views`).
- **FR-003**: Each GCD scenario MUST be checked independently — a failure
  in GCD-008 must not skip GCD-009. The harness MUST use a fail
  accumulator (like `comfygo-live-validate`) rather than `set -e`.
- **FR-004**: The harness MUST assert both exit code AND output content
  for each scenario. Exit code alone is insufficient (error gates expect
  exit 1, apply expects exit 0).
- **FR-005**: The harness MUST capture an evidence directory with
  per-scenario logs (stdout, stderr, exit code, filesystem pre/post snapshot),
  full harness stdout/stderr, and redacted/capped filesystem listings. Evidence
  MUST NOT record token values, marker JSON contents, or unredacted live model
  root paths.
- **FR-006**: The harness MUST exit 0 only if ALL scenarios pass. Any
  single failure results in exit 1 and a summary of which scenarios
  failed.
- **FR-007**: The harness MUST NOT create `.comfygo_trash/` during any
  dry-run or error-gate scenario.
- **FR-008**: Apply validation scenarios (GCD-014, GCD-015) MUST run in a temp
  root only. The harness MUST refuse to run scenario apply checks against a
  live model root. Live targeted GC quarantine, if requested as a real action,
  MUST use `--apply targeted-gc --gc-target <name>` and the same guided
  confirmation/readiness gates.
- **FR-009**: The harness MUST print a per-scenario PASS/FAIL line for
  every GCD-ID, and a final summary.
- **FR-010**: The feature MUST be reachable from a single comfygo entry
  point that reports both registry readiness and GC doctor readiness.
- **FR-011**: The final summary MUST include a clear next action. When all
  readiness checks pass, it MUST list all currently available safe actions the
  user may run next. When checks fail or live-root readiness is unknown, it
  MUST name the blocked actions, the blocking issue, and the next diagnostic
  or setup action.
- **FR-012**: If an actual model root is supplied or configured, the harness
  MUST run only read-only GC smoke checks against that root and MUST verify
  that `.comfygo_trash/` is not created or modified by those checks.
- **FR-013**: The guided entry point MUST NOT execute a real mutating action
  merely because readiness checks pass. It may run a listed safe action only
  after explicit user confirmation in the same flow or when invoked with an
  explicit apply/fix flag. In non-interactive execution, `--yes` is also
  required for mutation.
- **FR-014**: The guided entry point MUST distinguish available safe actions
  from blocked actions in its summary, so users can see what can proceed now
  and what condition must be resolved before other actions are available.
- **FR-015**: The guided entry point MUST evaluate the full comfygo action
  catalog: runtime node sync, patch application, model-view reconcile,
  targeted GC quarantine, launch/restart, install/update, and upstream
  refresh. It MUST report each action as available, blocked, or not relevant
  for the current state.
- **FR-016**: The final summary MUST show the complete action inventory and
  exactly one recommended next action selected from the currently available
  actions. The recommendation MUST be based on dependency order and safety,
  not on arbitrary command ordering.
- **FR-017**: The recommended-next-action order MUST be safety-first:
  setup/configuration readiness, runtime node sync, and patch application
  precede model-view reconcile; reconcile precedes targeted GC quarantine;
  targeted GC precedes launch/restart; install, update, and upstream refresh
  are recommended only when explicitly requested or when they are clearly
  blocking progress.
- **FR-018**: The guided entry point MUST use `targeted-gc` as the only stable
  action id for GC quarantine. It MUST refuse aliases such as `gc-target`.
- **FR-019**: The guided entry point MUST NOT hide prerequisite mutations behind
  launch or restart. If launch/restart helpers would sync, install, patch, or
  reconcile, launch/restart MUST remain blocked until those prerequisite
  actions are already no-op or a pure launch/restart helper is used.
- **FR-020**: The GC doctor temp root MUST be newly created under an allowed
  temporary parent, non-symlinked by `lstat`, resolved strictly, and disjoint
  from every configured or supplied live model root before any fixture is
  created or any apply scenario is run.

### Repository Policy Requirements

- Features that invoke Python or comfy-cli commands MUST use uv-first
  command forms: `uv run`.
- Features MUST NOT introduce direct `pip`, `python -m pip`, or unwrapped
  `python` workflow commands.
- No tokens, model files, generated views, caches, logs, user prompts, or
  local runtime state may be committed to this repo.
- Code that references model root paths MUST use configurable variables
  or environment variables, not hard-coded absolute paths.

### Key Entities

- **GCD Scenario**: A single test case from the doctor matrix, identified
  by a stable ID (GCD-001 through GCD-016), with a defined fixture setup,
  command, expected exit code, and expected output pattern.
- **Fixture Folder**: A folder under the temp model root created by the
  harness before scenarios run. Fixtures have known names and contents
  that scenarios depend on.
- **Evidence Directory**: A dated directory under `/tmp/comfygo-gc-doctor.*/`
  containing per-scenario logs, exit codes, and filesystem snapshots.
- **Next Action**: The user-facing instruction emitted after readiness checks
  that tells the user which real command/action is safe to run next, or what
  must be fixed before proceeding.
- **Available Safe Action**: A real action whose prerequisites are satisfied
  by the current readiness checks and that may be run after explicit
  confirmation or an explicit apply/fix flag.
- **Blocked Action**: A real action the guided entry point can identify but
  must not offer to run yet because one or more readiness conditions failed or
  are unknown.
- **Action Catalog**: The complete set of comfygo operations the guided entry
  point evaluates for readiness: sync, patch, reconcile, targeted GC,
  launch/restart, install/update, and upstream refresh.
- **Recommended Next Action**: The single available action highlighted after
  the inventory as the best next step based on dependency order and safety.
- **Safety-First Order**: The recommendation policy that prefers prerequisite
  setup, sync, patch, reconcile, and targeted cleanup before launch/restart,
  and avoids broad install/update/upstream refresh work unless requested or
  blocking.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The harness exits 0 on a clean run through all 16 GCD
  scenarios.
- **SC-002**: The harness exits 1 and reports which scenario failed when
  any single GCD scenario is made to fail (e.g., by corrupting a fixture).
- **SC-003**: No `.comfygo_trash/` directory is created by dry-run or
  error-gate scenarios (GCD-001 through GCD-013).
- **SC-004**: Apply scenarios (GCD-014, GCD-015) only mutate files under
  the temp root, never outside it.
- **SC-005**: The evidence directory contains at minimum: a per-scenario
  log, the full harness stdout/stderr, and a filesystem listing before
  and after each apply scenario.
- **SC-006**: The harness completes all 16 scenarios in under 30 seconds
  on a typical development machine.
- **SC-007**: A user can run one comfygo entry point and see registry
  readiness, GC doctor readiness, and the exact next safe action without
  knowing separate subcommands in advance.
- **SC-008**: When an actual model root is supplied, the harness completes
  read-only smoke checks without creating or modifying `.comfygo_trash/`.
- **SC-009**: When more than one safe action is available, the final summary
  lists all currently available actions and does not hide alternatives behind
  a single recommendation.
- **SC-010**: A clean readiness run without confirmation or an explicit
  apply/fix flag performs no real mutating action.
- **SC-011**: The final summary accounts for every action in the full comfygo
  action catalog, either as available, blocked with a reason, or not relevant
  to the current state.
- **SC-012**: When multiple actions are available, the final summary includes
  exactly one recommended next action and explains the dependency or safety
  reason for choosing it.
- **SC-013**: The recommended next action follows the safety-first order and
  does not recommend install, update, or upstream refresh ahead of local
  sync/patch/reconcile/GC work unless explicitly requested or blocking.

## Assumptions

- The `scripts/comfygo-models.sh` wrapper exists and is executable.
- The GC feature (feature 002) code is present and the existing test
  suite passes.
- `uv` is available in the execution environment.
- The temp root is on a local filesystem that supports symlinks and
  `os.rename()` (POSIX).
- The harness does NOT require a running ComfyUI.
- The single entry point can resolve the model root from existing comfygo
  configuration or from an explicit user-supplied model-root argument.
- All scenarios run in a single temp root to avoid per-scenario setup
  overhead. The harness must reset state between apply scenarios (e.g.,
  by recreating the temp root).
- The `doctor-matrix.md` document is the source of truth for fixture
  names, commands, expected outputs, and exit codes. Any discrepancy
  between this spec and the matrix should be resolved in favor of the
  matrix.
