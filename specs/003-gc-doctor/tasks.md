# Tasks: GC Doctor - guided comfygo operations

**Input**: Design documents from `/specs/003-gc-doctor/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/README.md`, `quickstart.md`, and `specs/002-model-gc/doctor-matrix.md`

**Tests**: Required by the feature spec. Write/adjust tests before the matching implementation tasks and verify they fail for missing behavior before making them pass.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently after the shared foundation is complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches a different file or independent test case
- **[Story]**: User story label from `specs/003-gc-doctor/spec.md`
- Every task includes exact repository paths

## Repository Rules For Generated Tasks

- Python and comfy-cli commands must use uv-first command forms such as `uv run`.
- Do not add direct `pip`, `python -m pip`, or unwrapped `python` workflow commands.
- Do not commit tokens, model weights, generated logs, caches, runtime histories, local prompts, or live `.comfygo_trash/` contents.
- Keep live model-root GC checks read-only. Apply-mode GC scenarios are allowed only under temporary roots.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the test harness and confirm the source documents that drive implementation.

- [X] T001 Confirm `specs/003-gc-doctor/spec.md`, `specs/003-gc-doctor/plan.md`, `specs/003-gc-doctor/contracts/README.md`, and `specs/002-model-gc/doctor-matrix.md` contain no unresolved `NEEDS CLARIFICATION` markers before implementation.
- [X] T002 [P] Extend subprocess helpers in `custom_nodes/comfygo_model_registry/tests/test_doctor.py` so tests can run both `scripts/comfygo` and `scripts/comfy-local` with `UV_CACHE_DIR=/tmp/uv-cache` and isolated `COMFY_LOCAL_CONFIG`.
- [X] T003 [P] Add fake ComfyUI, comfy-cli, model-root, runtime-registry-copy, and patch-state fixture builders in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T004 [P] Add GCD fixture helpers in `custom_nodes/comfygo_model_registry/tests/test_doctor.py` using the exact names from `specs/002-model-gc/doctor-matrix.md`, including success-cleanup and failure-retention fixture paths.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the reusable doctor machinery that all user stories depend on.

**Critical**: No user story implementation should begin until this phase is complete.

- [X] T005 Extend `scripts/comfy-local` doctor argument parsing and dispatch so `doctor "$@"` supports `--models-dir <path>`, `--apply <action-id>`, `--gc-target <name>`, `--yes`, `--keep-evidence`, `--help`, and invalid-argument exit code 2.
- [X] T006 Add the full doctor action catalog in `scripts/comfy-local` for `runtime-envrc`, `sync`, `patch-comfyui`, `patch-cli`, `reconcile`, canonical `targeted-gc`, `launch`, `restart`, `install`, `update`, and `refresh-upstreams`; reject aliases such as `gc-target`.
- [X] T007 Add action status formatting helpers in `scripts/comfy-local` that print each catalog action as `available`, `blocked`, or `not relevant` with a reason and a same-entry command such as `scripts/comfygo doctor --apply <action-id>` when applicable.
- [X] T008 Refactor existing readiness checks in `scripts/comfy-local` into probe helpers that record pass/fail state without exiting early.
- [X] T009 Add an evidence-directory helper in `scripts/comfy-local` that creates `/tmp/comfygo-doctor.XXXXXX`, captures full harness stdout/stderr plus per-probe logs, redacts live roots and token-like values, caps filesystem snapshots, and avoids storing marker JSON contents.
- [X] T010 Add read-only snapshot helpers in `scripts/comfy-local` for `.comfygo_views/` and `.comfygo_trash/` state before and after doctor probes.
- [X] T011 Add a GC temp-root scenario runner skeleton in `scripts/comfy-local` that shells out through `scripts/comfygo-models.sh`, accumulates failures instead of relying on `set -e`, creates temp roots with `mktemp -d`, rejects symlinked or live-root-overlapping temp paths before fixture creation, cleans the temp root on success, and retains/prints temp root plus evidence paths on failure or `--keep-evidence`.
- [X] T012 Add a live model-root GC dry-run smoke helper in `scripts/comfy-local` that accepts the resolved `--models-dir` path, snapshots `.comfygo_trash/` before and after read-only checks, and refuses every bulk/no-target live GC apply path.
- [X] T013 Add the safety-first recommendation function in `scripts/comfy-local` that selects exactly one recommended available action and prints the dependency/safety rationale.
- [X] T014 Add the explicit apply dispatcher in `scripts/comfy-local` that recomputes readiness, refuses unknown/blocked/not-relevant actions with exit 2, prompts `Run <action-id> now? [y/N]` on TTY, requires `--yes` in non-interactive mode, and delegates only to existing safe commands.
- [X] T015 Update the `doctor` usage text in `scripts/comfy-local` so the same entry point documents readiness inventory and explicit `--apply <action-id>` execution.

**Checkpoint**: Foundation ready. User story implementation can now proceed.

---

## Phase 3: User Story 1 - Guided Readiness And Dry-Run Validation (Priority: P1)

**Goal**: `scripts/comfygo doctor` lists the full action inventory, runs registry readiness and GC dry-run validation, stays read-only by default, prints the recommended next action, and blocks mutating actions until the full 16-scenario GC doctor pass is available.

**Independent Test**: Run `scripts/comfygo doctor` against fake runtime paths and a temp model root. It exits 0 when probes pass, prints all action statuses, prints exactly one recommended next action, and writes PASS lines for GCD-001 through GCD-008.

### Tests for User Story 1

- [X] T016 [P] [US1] Add `test_doctor_lists_full_action_inventory` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py` for every action id from `specs/003-gc-doctor/contracts/README.md`, and assert alias ids such as `gc-target` are refused with exit 2.
- [X] T017 [P] [US1] Add `test_doctor_prints_exactly_one_recommended_next_action_with_rationale` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T018 [P] [US1] Add `test_doctor_default_run_does_not_mutate_runtime_or_model_root` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T019 [P] [US1] Add `test_doctor_runs_gcd_001_through_008_with_pass_lines` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T020 [P] [US1] Add `test_doctor_live_gc_smoke_is_read_only_with_models_dir` and `test_doctor_without_runtime_env_reports_live_root_unknown` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.

### Implementation for User Story 1

- [X] T021 [US1] Implement the default `Comfygo readiness`, `Evidence`, `Checks`, `Actions`, and `Recommended next action` output sections in `scripts/comfy-local`, including the dependency/safety rationale.
- [X] T022 [US1] Wire existing registry readiness, runtime copy readiness, patch readiness, and model-view reconcile dry-run results into action statuses in `scripts/comfy-local`.
- [X] T023 [US1] Implement GCD-001 through GCD-008 dry-run and symlink scenarios in the GC temp-root runner in `scripts/comfy-local`.
- [X] T024 [US1] Capture per-scenario stdout, stderr, exit code, and pre/post filesystem snapshots for GCD-001 through GCD-008 under the evidence directory in `scripts/comfy-local`.
- [X] T025 [US1] Run the live model-root GC dry-run smoke from `scripts/comfy-local` only when a model root is configured or supplied through `--models-dir`; otherwise report live-root readiness as unknown and block dependent actions with the next setup/configuration action.
- [X] T026 [US1] Ensure `scripts/comfy-local` exits 0 when inventory is computed and required temp-root probes pass, while keeping mutating actions blocked until `PASS: all 16 GCD scenarios` is available.

**Checkpoint**: User Story 1 is independently usable as a read-only readiness inventory. Mutating actions remain blocked until US2 and US3 complete the full 16-scenario GC safety gate.

---

## Phase 4: User Story 2 - Error Gate Validation (Priority: P1)

**Goal**: The doctor harness proves GC fails closed for invalid, missing, ambiguous, multi-match, and unsafe-name apply requests without mutating files.

**Independent Test**: Run the doctor harness with temp fixtures. GCD-009 through GCD-013 each report PASS, source folders remain unchanged, and no `.comfygo_trash/` is created.

### Tests for User Story 2

- [X] T027 [P] [US2] Add `test_doctor_runs_gcd_009_through_013_with_no_trash` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T028 [P] [US2] Add `test_doctor_reports_failed_gcd_id_when_one_scenario_fails` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T029 [P] [US2] Add `test_doctor_apply_refuses_unknown_blocked_and_not_relevant_actions_with_exit_2` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T030 [P] [US2] Add `test_doctor_yes_does_not_bypass_blocked_action_checks` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.

### Implementation for User Story 2

- [X] T031 [US2] Implement GCD-009 through GCD-013 in the GC temp-root runner in `scripts/comfy-local` with exact exit-code and output assertions from `specs/002-model-gc/doctor-matrix.md`.
- [X] T032 [US2] Add source-unchanged and no-trash assertions for GCD-009 through GCD-013 in `scripts/comfy-local`.
- [X] T033 [US2] Add fail-accumulator reporting in `scripts/comfy-local` so one failed GCD scenario reports its ID but does not skip later scenarios.
- [X] T034 [US2] Implement `doctor --apply <action-id>` refusal output and exact exit code 2 in `scripts/comfy-local` for unknown, blocked, and not-relevant actions.
- [X] T035 [US2] Ensure `--yes` in `scripts/comfy-local` only suppresses prompts and never changes action readiness or blocked-action refusal rules.

**Checkpoint**: Error gates are validated without file mutation.

---

## Phase 5: User Story 3 - Apply And Idempotency Validation (Priority: P2)

**Goal**: The doctor harness validates successful quarantine and second-apply idempotency in temp roots only, while real actions run only through explicit confirmation or `--apply`.

**Independent Test**: Run the doctor harness. GCD-014 quarantines exactly one temp folder and GCD-015 exits 1 while leaving the quarantine unchanged. Default doctor still runs no real mutating action.

### Tests for User Story 3

- [X] T036 [P] [US3] Add `test_doctor_runs_gcd_014_and_015_sequentially` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py` and GC-level regression coverage in `custom_nodes/comfygo_model_registry/tests/test_gc.py` for destination recheck and post-rename metadata assertions.
- [X] T037 [P] [US3] Add `test_doctor_apply_sync_recomputes_readiness_and_delegates_to_sync` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T038 [P] [US3] Add `test_doctor_apply_targeted_gc_requires_valid_gc_target` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py` covering missing target, no match, multiple matches, symlink target, unsafe target, and one successful unique managed target.
- [X] T039 [P] [US3] Add `test_doctor_default_does_not_run_available_mutating_action` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.

### Implementation for User Story 3

- [X] T040 [US3] Implement sequential GCD-014 and GCD-015 apply/idempotency scenarios in `scripts/comfy-local` using only a temporary model root.
- [X] T041 [US3] Add quarantine mutation and evidence assertions for GCD-014 and GCD-015 in `scripts/comfy-local`, including source removal, exact trash creation, unchanged second-apply trash state, pre/post filesystem listings, per-scenario stdout/stderr/exit logs, and post-rename metadata checks in `custom_nodes/comfygo_model_registry/gc.py`.
- [X] T042 [US3] Implement explicit apply delegation in `scripts/comfy-local` for `runtime-envrc`, `sync`, `patch-comfyui`, `patch-cli`, `reconcile`, `install`, `update`, and `refresh-upstreams`.
- [X] T043 [US3] Implement `targeted-gc` in `scripts/comfy-local` only for `--apply targeted-gc --gc-target <name>` after all 16 GCD scenarios pass; reject bulk/no-target live GC apply and validate the target as a unique managed non-symlink folder before delegating to `scripts/comfygo-models.sh`.
- [X] T044 [US3] Add pure `launch` and `restart` apply paths in `scripts/comfy-local`, or keep those actions blocked until existing launch/restart helpers are proven no-op for sync, install, patch, and reconcile prerequisite work.
- [X] T045 [US3] Add interactive confirmation in `scripts/comfy-local` for TTY runs without `--yes`, and make non-interactive `--apply` without `--yes` exit 2 without mutation.

**Checkpoint**: This is the first point where doctor may report real mutating actions as available, because all 16 GCD scenarios, refusal gates, and apply/idempotency checks are covered.

---

## Phase 6: User Story 4 - Flag Ordering Compatibility (Priority: P2)

**Goal**: GC and doctor model-root routing works when `--models-dir` is supplied explicitly, and `scripts/comfygo-models.sh` accepts the GCD-016 flag ordering.

**Independent Test**: Run `scripts/comfygo-models.sh gc --models-dir "$DIR"` with a managed fixture and run `scripts/comfygo doctor --models-dir "$DIR"` with a read-only model root. Both commands use the supplied path and do not create `.comfygo_trash/`.

### Tests for User Story 4

- [X] T046 [P] [US4] Update `test_wrapper_gc_models_dir_after_subcommand_dry_run` in `custom_nodes/comfygo_model_registry/tests/test_wrapper.py` to use the exact GCD-016 fixture name `ManagedDownloader`.
- [X] T047 [P] [US4] Add `test_wrapper_gc_models_dir_before_subcommand_matches_after_subcommand` in `custom_nodes/comfygo_model_registry/tests/test_wrapper.py`.
- [X] T048 [P] [US4] Add `test_doctor_models_dir_argument_drives_reconcile_and_gc_smoke` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.
- [X] T049 [P] [US4] Add `test_doctor_live_smoke_does_not_report_reserved_categories_as_ambiguous` in `custom_nodes/comfygo_model_registry/tests/test_doctor.py`.

### Implementation for User Story 4

- [X] T050 [US4] Ensure `scripts/comfygo-models.sh` preserves identical behavior for `--models-dir "$DIR" gc` and `gc --models-dir "$DIR"`.
- [X] T051 [US4] Pass the explicit doctor `--models-dir` value from `scripts/comfy-local` into reconcile dry-run, GC live dry-run smoke helpers, and every recommended/delegated model command so root precedence cannot drift between wrappers.
- [X] T052 [US4] Add reserved ComfyUI category assertions for `diffusion_models`, `loras`, `vae`, `text_encoders`, and `checkpoints` in the live GC smoke helper in `scripts/comfy-local`.

**Checkpoint**: Explicit model-root routing is consistent through wrapper and doctor paths.

---

## Phase 7: Polish And Cross-Cutting Validation

**Purpose**: Keep docs, contracts, and generated artifacts aligned after implementation.

- [X] T053 [P] Update `README.md` and `docs/model-library.md` to describe guided `scripts/comfygo doctor`, action inventory, recommended next action, `--gc-target`, prompt behavior, exact refusal exit code 2, and explicit `--apply <action-id>` execution.
- [X] T054 [P] Update `specs/003-gc-doctor/contracts/README.md` and `specs/003-gc-doctor/quickstart.md` if implemented command flags or output text differ from the current contract.
- [X] T055 [P] Re-check `specs/002-model-gc/doctor-matrix.md` against implemented GCD scenario names, command lines, exit codes, and output assertions.
- [X] T056 Run `UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line -p no:cacheprovider` for `custom_nodes/comfygo_model_registry/tests`.
- [X] T057 Run `bash -n scripts/comfy-local` and `bash -n scripts/comfygo-models.sh` for shell syntax validation.
- [X] T058 Run `git diff --check` for whitespace validation across the repository.
- [X] T059 Run focused smoke commands from `specs/003-gc-doctor/quickstart.md` against temp roots only, including `scripts/comfygo doctor`, `scripts/comfygo doctor --models-dir "$TMP_MODELS"`, blocked-action exit 2 probes, and `scripts/comfygo doctor --yes --apply sync` with fake runtime paths.
- [X] T060 Scan `scripts/`, `custom_nodes/comfygo_model_registry/tests/`, `docs/`, and `specs/003-gc-doctor/` for committed machine-local paths, tokens, caches, pycache, model weights, unredacted evidence paths, evidence logs, and `.comfygo_trash/` contents.
- [X] T061 Run a timed validation for `scripts/comfygo doctor --keep-evidence` against local temp roots and fail if the 16-scenario GC doctor pass exceeds 30 seconds.
- [X] T062 Run the Spec Kit consistency pass for `specs/003-gc-doctor/spec.md`, `specs/003-gc-doctor/plan.md`, and `specs/003-gc-doctor/tasks.md` and append any remaining implementation gaps before declaring the feature complete.

---

## Dependencies And Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2. This is readiness inventory only; mutating actions stay blocked until all 16 GCD scenarios are implemented.
- **Phase 4 US2**: Depends on Phase 2 and can proceed in parallel with US1 after shared GC runner scaffolding exists.
- **Phase 5 US3**: Depends on Phase 4 for the fail-closed and no-mutation checks.
- **Phase 6 US4**: Wrapper flag-order tests can start after Phase 2; doctor `--models-dir` routing tasks depend on US1 doctor wiring.
- **Phase 7 Polish**: Depends on the desired user stories being complete.

### User Story Dependencies

- **US1 (P1)**: No dependency on other user stories after foundation.
- **US2 (P1)**: No dependency on US1 output, but uses the same foundational GCD runner.
- **US3 (P2)**: Depends on US2 safety gates so apply validation is built on proven fail-closed behavior.
- **US4 (P2)**: Wrapper ordering is independent after foundation; doctor model-root routing depends on US1 output sections and argument parsing.

### Within Each User Story

- Write or adjust tests first.
- Run the new tests and confirm they fail for missing behavior.
- Implement the story.
- Run the story tests, then run the full registry test command in Phase 7.

---

## Parallel Examples

### User Story 1

```text
Task: T016 test full action inventory in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T017 test exactly one recommendation with rationale in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T018 test default no mutation in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T019 test GCD-001 through GCD-008 in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T020 test live GC smoke read-only behavior and missing-root unknown state in custom_nodes/comfygo_model_registry/tests/test_doctor.py
```

### User Story 2

```text
Task: T027 test GCD-009 through GCD-013 no-trash behavior in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T028 test failed GCD reporting in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T029 test refused apply actions in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T030 test --yes does not bypass blocked actions in custom_nodes/comfygo_model_registry/tests/test_doctor.py
```

### User Story 4

```text
Task: T046 update GCD-016 wrapper fixture in custom_nodes/comfygo_model_registry/tests/test_wrapper.py
Task: T047 compare before/after --models-dir ordering in custom_nodes/comfygo_model_registry/tests/test_wrapper.py
Task: T048 test doctor --models-dir routing in custom_nodes/comfygo_model_registry/tests/test_doctor.py
Task: T049 test reserved category live smoke behavior in custom_nodes/comfygo_model_registry/tests/test_doctor.py
```

---

## Implementation Strategy

### Minimum Safe Implementation

1. Complete Phase 1.
2. Complete Phase 2.
3. Complete Phase 3, Phase 4, and Phase 5.
4. Validate that `scripts/comfygo doctor` reports `PASS: all 16 GCD scenarios` before any mutating action is available.

### Incremental Delivery

1. Add US1 guided readiness inventory and dry-run validation; mutating actions remain blocked.
2. Add US2 error gate validation.
3. Add US3 temp-root apply/idempotency validation and explicit action execution; this is the first increment that can offer real mutating actions.
4. Add US4 model-root flag ordering compatibility.
5. Run Phase 7 validation before marking the feature complete.

### Safety Boundary

- Default doctor is read-only.
- Temp-root GCD apply checks are allowed.
- Live model-root GC apply is forbidden.
- Real sync, patch, reconcile, launch, restart, install, update, and upstream refresh actions require explicit confirmation or `--apply <action-id>`.

## Phase 8: Convergence

(Added by speckit-converge to capture gaps between spec/plan/tasks intent and current codebase.)

- [ ] T063 Reconcile guided doctor implementation location: the spec (FR-010, FR-015..), plan, and tasks (T005-T015, T021-T026, T034) require extending scripts/comfy-local `doctor` with action inventory, recommended-next, --apply support and GCD harness inside the single comfygo entry point. Current code implements GCD scenarios only in scripts/comfygo-verify and leaves doctor() as legacy registry checks (missing).
- [ ] T064 Ensure or document that `comfygo doctor` (not only verify) performs the full 16 GCD scenarios + prints PASS lines + blocks mutating actions until `PASS: all 16 GCD scenarios` as per US1/US2 acceptance and SCs (partial in verify only).
- [ ] T065 Reconcile test coverage: tasks T016-T020, T027 etc. expect new tests in custom_nodes/comfygo_model_registry/tests/test_doctor.py for doctor inventory/recommendation/GCD/live smoke. Current test_doctor.py only has legacy registry tests (partial/missing for the guided flow).
- [ ] T066 Review whether the split (doctor for registry + verify for GCD) contradicts the "single comfygo entry point" and "extend doctor" decisions in plan/research; if intentional, update spec/plan or implement the guided behaviors in doctor as originally specified (contradicts plan decision).
- [ ] T067 (from test subagent cross-check) Confirm after excludes that no test scaffolding from this feature's harness leaks into runtime installs (related hygiene for verifiable flows).

**Summary at time of converge**: Multiple high-severity gaps around the core "guided single-entry doctor" promise vs actual code placement. These should be reviewed before marking 003 complete or when porting patterns to later features.
