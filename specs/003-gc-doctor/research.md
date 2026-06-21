# Research: GC Doctor - guided comfygo operations

## Decision: Extend `comfygo doctor` as the single readiness entry point

**Decision**: The feature extends the existing `comfygo doctor` path instead
of creating a separate `comfygo-verify` or `comfygo-gc-doctor` command.

**Rationale**: The user wants one entry point that says what can be done and
what is next. `comfygo doctor` is already the readiness/status command, so
adding action inventory and recommendation there minimizes command
memorization.

**Alternatives considered**:
- Separate `scripts/comfygo-gc-doctor`: good for isolated GC tests, but does
  not solve the "what can I do next?" workflow.
- Separate `scripts/comfygo-verify`: useful for CI, but too repo-test oriented
  and not a guided operations surface.
- New `comfygo guide`: clearer name, but creates another command to remember.

## Decision: Read-only by default, explicit action execution

**Decision**: The default readiness run prints action states and a recommended
next action, but performs no real mutation. A real action can run only after
interactive confirmation or an explicit apply/fix flag naming the action.

**Rationale**: This preserves the safety expectation of doctor while still
letting the same entry point carry the user forward.

**Alternatives considered**:
- Recommend only: safe, but forces users to remember separate commands.
- Auto-run after checks pass: convenient, but violates the safe daily operation
  principle and increases blast radius.

## Decision: Full comfygo action catalog

**Decision**: The readiness flow evaluates sync, patch, reconcile, targeted GC,
launch/restart, install/update, and upstream refresh.

**Rationale**: The user's operational question is not GC-only; they want to
know what can be done next across the app.

**Alternatives considered**:
- GC-only: too narrow.
- Registry + GC only: misses sync, patch, launch, install/update, and upstream
  refresh decisions that block the real workflow.

## Decision: Safety-first recommended order

**Decision**: The recommended next action is selected in this order:

1. setup/configuration readiness
2. runtime node sync
3. patch application
4. model-view reconcile
5. targeted GC cleanup
6. launch/restart
7. install/update/upstream refresh only when explicitly requested or blocking

**Rationale**: This order handles prerequisites and local safety before launch,
while avoiding broad updates unless the user asked for them or they block
progress.

**Alternatives considered**:
- Runtime-first: can launch against stale or unsynced state.
- Update-first: unnecessarily broad and conflicts with explicit upstream
  refresh policy.

## Decision: GC doctor combines temp-root scenario checks with live dry-run

**Decision**: The GCD matrix runs in temp roots for all scenarios, including
apply/idempotency checks. If a real model root is configured, the guided doctor
also runs a read-only GC dry-run smoke check against it.

**Rationale**: Temp roots prove the implementation's safety gates. Live dry-run
proves the actual model root can be inspected without mutation.

**Alternatives considered**:
- Temp-root only: not useful enough for real operations.
- Live apply tests: unsafe and contrary to the GC feature contract.

## Decision: Evidence follows existing live validator style

**Decision**: The flow writes temporary evidence logs for readiness probes and
GC scenario results, using the `comfygo-live-validate` style.

**Rationale**: Existing tests already expect evidence-path reporting for live
validation failures, and it gives useful debugging artifacts without committing
logs.

**Alternatives considered**:
- Console-only: harder to diagnose.
- Repo-local evidence: risks committing runtime/log state.
