---
description: "Task list for model-gc feature implementation"
---

# Tasks: Model Garbage Collection (comfygo models gc)

**Input**: Design documents from `specs/002-model-gc/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md

**Tests**: Tests are REQUIRED — TDD pattern (write tests first, ensure they FAIL before implementation). The existing test suite covers scanner/descriptor/reconciler; add GC-specific tests in test_gc.py. All test commands use `uv run pytest ...`

**Organization**: Tasks are grouped by user story (from spec.md) to enable independent implementation and testing of each story. US1 is pre-existing (from 001) and treated as a verification story under this feature.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g. [US1], [US2])
- Include exact file paths in descriptions

## Repository Rules For Generated Tasks

- Python and comfy-cli tasks MUST use uv-first command forms: `uv run`, `uv pip --python <workspace-python>`, or `uv run --python <workspace-python> --no-project python ...`.
- Do not generate tasks that use direct `pip`, `python -m pip`, or unwrapped `python` workflow commands. If `uv` is unavailable, task the user to install `uv` first instead of adding a fallback installer/interpreter.

## Path Conventions

- **Custom node code**: `custom_nodes/comfygo_model_registry/`
- **Tests**: `custom_nodes/comfygo_model_registry/tests/`
- **CLI wrapper**: `scripts/comfygo-models.sh`
- **Docs**: `docs/model-library.md`
- **GC module**: NEW `custom_nodes/comfygo_model_registry/gc.py` (reuses models.py, scanner.py for policy only, descriptor.py for marker parsing)
- GC MUST follow v1 constraint: raw `models_dir.iterdir()` only; MUST NOT delegate discovery/classification to `scanner.scan_models()` (per spec FR-015 and plan).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create gc.py module skeleton + data classes, test file, extend CLI parser, confirm wrapper forwarding. No user story work until Setup + Foundational complete.

- [X] T001 Create `custom_nodes/comfygo_model_registry/gc.py` skeleton (module docstring, imports: pathlib, os, json, datetime, dataclasses, typing; from . import models, scanner, descriptor; pass for functions). Acceptance: imports cleanly with `uv run python -c "import custom_nodes.comfygo_model_registry.gc"`.
- [X] T002 [P] Create `custom_nodes/comfygo_model_registry/tests/test_gc.py` skeleton with pytest, imports, and fixtures: tmp model root via tmp_path, helpers to create managed folders (with .comfygo-download.json and comfygo-model.json), ambiguous folders, reserved folders, hidden folders, source-symlink cases. Acceptance: `uv run pytest custom_nodes/comfygo_model_registry/tests/test_gc.py --collectonly -q` succeeds with no import errors.
- [X] T003 [P] Extend `custom_nodes/comfygo_model_registry/cli.py` build_parser(): add `gc` subparser alongside "reconcile". Add shared-style `-f/--filter` (dest="gc_filter" or reuse pattern) and `--apply` flag. Gate must be enforceable in main/dispatch. Acceptance: `uv run python -m custom_nodes.comfygo_model_registry.cli gc --help` shows the options.
- [X] T004 [P] Verify `scripts/comfygo-models.sh` forwards `gc` + `--models-dir`, `-f`, `--apply` via EXTRA_ARGS (current design already collects post --models-dir into PY_ARGS). If needed add explicit comment or test coverage. Add/update regression test in `custom_nodes/comfygo_model_registry/tests/test_wrapper.py` that invokes wrapper script with gc subcommand and asserts it reaches CLI (no crash on parse). Use uv run forms.

**Checkpoint**: Project structure ready for GC. CLI parser stub exists. Wrapper path confirmed.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core GC scan/classify/safety/collision primitives. **CRITICAL** — blocks all user stories. Implement using data-model.md entities. Reuse validate_path_segment (models.py) and reserved list (scanner.py _RESERVED_CATEGORY_FOLDERS). Raw iterdir only.

- [X] T005 [P] In `custom_nodes/comfygo_model_registry/gc.py`: define data classes exactly per data-model.md: `Marker`, `ManagedFolder`, `AmbiguousFolder`, `SkippedFolder`, `QuarantineOperation`, `GCReport`. Include `apply_requested`, `apply_filter`, `selected_target`, `errors`. Acceptance: can instantiate and round-trip fields; matches spec contracts.
- [X] T006 [P] Implement `detect_markers(folder: pathlib.Path) -> list[Marker]` in gc.py. Check for `.comfygo-download.json` (type="downloader") and `comfygo-model.json` (type="descriptor"). For each present: record path + parseable (try json.load else False). Empty/unparseable marker still counts as presence (per FR-015 edge case + contracts). Acceptance: detects both; returns parseable=False for bad JSON; unit-testable.
- [X] T007 Implement `scan_managed_folders(models_dir: pathlib.Path)` (and supporting classify) in gc.py. MUST use raw `for entry in models_dir.iterdir():` (v1 constraint FR-015). Skip hidden and reserved category names first so they remain silent, then classify source symlinks as SkippedFolder(reason="source symlink") with a warning, then non-directories, then candidate directories. For each candidate: call detect_markers; if any markers → ManagedFolder else AmbiguousFolder. Never call scanner.scan_models() or use packages.ambiguous. Add comment: "# Per plan + FR-015: raw iterdir; preserve symlink info; no scanner delegation; top-level only (no extra_roots)". Return structures for report (managed, ambiguous, skipped). Acceptance: matches quickstart scenarios on temp dirs; no scanner import used for discovery.
- [X] T008 Implement `.comfygo_trash` safety helpers in gc.py (or private fns):
  - validate all path segments with models.validate_path_segment(segment, context=...)
  - refuse if `.comfygo_trash` itself is_symlink()
  - refuse if date subdir would be symlink
  - treat existing dest (dir/file/symlink/broken) as collision → append -N suffix (never overwrite)
  - refuse source if top-level entry was symlink (already in scan)
  - confirm source parent == models_dir (top-level only)
  - Never follow symlinks for quarantine decisions.
  Acceptance: all 7+ rules from T007/plan + FR-006/FR-011/FR-014 implemented and raise/warn appropriately.
- [X] T009 Implement collision suffix + quarantine destination computation: `compute_trash_dest(models_dir, name, date_str) -> Path`. If target exists (incl. symlink), try name-1, name-2... Warn on collision. In gc.py.
- [X] T010 Implement `quarantine(managed: ManagedFolder, models_dir: pathlib.Path, apply: bool) -> QuarantineOperation` skeleton (full in US3). Handle os.rename, EXDEV cross-fs (error "Cannot quarantine across filesystems; no files changed"), permission errors. Only mutate on apply. Fail-closed. In gc.py.

**Checkpoint**: GC can scan top-level raw, classify per marker presence, enforce all safety invariants on paths/trash. Ready for story impl. No mutations yet.

---

## Phase 3: User Story 1 - View-Side Stale Pruning (Priority: P1)

**Goal**: Confirm that view-side stale symlink pruning (via `comfygo models reconcile --apply`) continues to work as implemented in 001. GC command must not overlap or break reconcile/views behavior (FR-009). US1 is satisfied by pre-existing code; this phase verifies no regression from adding GC.

**Independent Test**: Run existing reconciler tests + a manual reconcile --apply on a temp dir with stale view; confirm views pruned correctly. GC dry-run or apply on same root must leave .comfygo_views handling untouched.

### Tests for User Story 1 (verify pre-existing)

- [X] T011 [P] [US1] Execute existing reconciler + compat_views tests to baseline: `uv run pytest custom_nodes/comfygo_model_registry/tests/test_reconciler.py custom_nodes/comfygo_model_registry/tests/test_compat_views.py -q --tb=line`. Record pass. Acceptance: all still green.
- [X] T012 [P] [US1] In test_gc.py or a shared test, create temp root + .comfygo_views + managed folders; invoke reconcile path (via import) after a simulated GC (no-op on views); assert views reconcile still detects/prunes stale symlinks correctly. Acceptance: no behavior change.

### Implementation / Verification for User Story 1

- [X] T013 [US1] Code-level check: ensure gc.py does not import or call anything from compat_views/reconciler for folder discovery. GC and reconcile are independent (FR-009). Add a comment in cli.py or gc.py. Acceptance: grep confirms separation.
- [X] T014 [US1] Run quickstart-style reconcile validation (if applicable) or confirm via existing docs that "stale views" scenario in US1 remains covered by reconcile --apply. No new GC code changes required for US1.

**Checkpoint**: US1 verified — reconcile view pruning unaffected. GC addition does not regress prior feature.

---

## Phase 4: User Story 2 - GC Dry-Run Inspection (Priority: P1) 🎯 MVP

**Goal**: `comfygo models gc` (and with `-f`) produces correct dry-run report of Managed (with marker:), Ambiguous, Warnings. No filesystem mutation. Default is always dry-run (FR-001). Supports filter.

**Independent Test**: Per spec: temp dir + marker folder → `gc` lists under "Managed folders"; no .comfygo_trash created. Ambiguous listed separately. Reserved/hidden/source-symlink handled per rules. Empty root → clean "nothing to report".

### Tests for User Story 2 (write FIRST, must FAIL before impl)

- [X] T015 [P] [US2] Test dry-run managed folder (`.comfygo-download.json`): assert "Managed folders:" section, correct path + "marker: downloader", exit 0, no .comfygo_trash dir created. In test_gc.py.
- [X] T016 [P] [US2] Test dry-run with `comfygo-model.json` descriptor marker: listed as "marker: descriptor".
- [X] T017 [P] [US2] Test ambiguous (no marker): listed under "Ambiguous" with "no marker file found". Never eligible.
- [X] T018 [P] [US2] Test `-f/--filter` (exact and substring): only matching entry appears in report; non-matches filtered.
- [X] T019 [P] [US2] Test empty model root: output is exactly "Nothing to report.", exit 0.
- [X] T020 [P] [US2] Test reserved (e.g. diffusion_models) + hidden (.foo) + non-dir: silently omitted from user report (or only in skipped internal).
- [X] T021 [P] [US2] Test empty/unparseable marker: still "Managed folders" + warning entry (exact per contracts/spec edge case).
- [X] T022 [P] [US2] Test source symlink: reported under Warnings with "warning: Refusing to quarantine symlinked folder..." (or skipped reason surfaced if filter matches); not listed as managed.
- [X] T023 [US2] Verify report format exactly matches contracts/README.md and spec examples (sections, indentation, "marker: ", "no marker file found"). Use capsys or similar.
- [X] T024 [US2] Verify raw iterdir contract: add assertion or monkeypatch that scanner.scan_models is NOT called during gc dry-run path.

### Implementation for User Story 2

- [X] T025 [US2] Implement `build_report(...)` and `format_report(report: GCReport) -> str` (or print inside run) in gc.py to produce exact sections: "Managed folders:\n  <path>\n    marker: <type>\n\nAmbiguous:\n...\nWarnings:\n...". Empty sections are omitted; if no managed, ambiguous, or warning entries remain after filtering, output exactly "Nothing to report." Include warnings for unparseable markers and source symlinks.
- [X] T026 [US2] Implement `run_gc(models_dir: Path, filter_str: str | None = None, apply: bool = False) -> GCReport` (or int exit) entrypoint in gc.py. For !apply: scan, optionally filter managed+ambiguous, print formatted report, return report (apply_requested=False). Must never mutate.
- [X] T027 [US2] Wire dispatch in `custom_nodes/comfygo_model_registry/cli.py` main(): `if args.command == "gc":` resolve filter (similar to reconcile_filter pattern), call gc.run_gc(models_dir, filter_str=..., apply=...) . Do NOT pass scanner packages. Handle output/errors to stderr/stdout. Add early gate? (apply gate in Phase 5).
- [X] T028 [US2] Add CLI integration test (or in test_cli.py): invoke via argparse or main() with "gc --models-dir <tmp>" and assert stdout contains expected sections. Do not require full folder_paths.
- [X] T029 [US2] Verify quickstart.md Scenario 1 (dry-run) and Scenario 2 (ambiguous) manually or via pytest using temp dir + script wrapper. `bash scripts/comfygo-models.sh gc --models-dir "$TMP"`.
- [X] T030 [US2] `uv run pytest custom_nodes/comfygo_model_registry/tests/test_gc.py -q -k "us2 or dry or managed or ambiguous" --tb=line` (all US2 tests pass after impl).

**Checkpoint**: User Story 2 (dry-run MVP) fully functional and testable independently. Users can inspect managed/ambiguous without risk. STOP and validate before US3.

---

## Phase 5: User Story 3 - GC Apply With Explicit Target (Priority: P2)

**Goal**: `comfygo models gc -f NAME --apply` quarantines exactly one targeted managed folder to `.comfygo_trash/<YYYY-MM-DD>/NAME/` (or -N on collision) via os.rename only. All safety rules + error cases enforced. Both `-f` AND `--apply` required for mutation (FR-001, FR-002, FR-013).

**Independent Test**: Per spec + quickstart: managed folder + `-f ... --apply` moves it (original gone), trash dated dir created if needed, only that folder, no other changes, no delete/copy. Re-run on same name → no-managed error, trash copy untouched. Ambiguous/missing/multi → error, no move. Symlink source/trash → refuse. Cross-fs → specific error.

### Tests for User Story 3 (TDD — write before full quarantine code)

- [X] T031 [P] [US3] Test successful quarantine: managed folder moves to trash/<date>/name/ ; source gone; other folders untouched; operation recorded in report. Verify with Path.exists().
- [X] T032 [P] [US3] Test repeated apply (idempotency FR-008): second `gc -f NAME --apply` → exit 1 + "No managed folder matching 'NAME'"; quarantined copy unchanged.
- [X] T033 [P] [US3] Test --apply without -f (gate): error exactly "error: --apply requires -f NAME", exit 1, no trash dir created. (Can be CLI level or dispatch.)
- [X] T034 [P] [US3] Test missing target: `gc -f Nonexistent --apply` → "No managed folder matching 'Nonexistent'", exit 1.
- [X] T035 [P] [US3] Test ambiguous rejection: folder no marker + `-f ... --apply` → "Folder 'NAME' is not managed by comfygo", exit 1.
- [X] T036 [P] [US3] Test multi-match: two managed "ModelOne","ModelTwo"; `-f Model --apply` → "Filter 'Model' matched multiple managed folders" + list, exit 1, nothing moved.
- [X] T037 [P] [US3] Test trash auto-create + date dir.
- [X] T038 [P] [US3] Test collision suffix: second same-name quarantine uses name-1 (or next free); warns.
- [X] T039 [P] [US3] Test source symlink refuse on apply: warning "Refusing to quarantine symlinked folder...", exit 1, no move.
- [X] T040 [P] [US3] Test symlinked .comfygo_trash refuse.
- [X] T041 [P] [US3] Test cross-filesystem (mock EXDEV or separate tmp on other fs if avail): error "Cannot quarantine across filesystems; no files changed", source untouched.
- [X] T042 [P] [US3] Test permission/rename failure: error reported (e.g. "Permission denied..."), source left in place.
- [X] T043 [P] [US3] Test unparseable marker still quarantinable with -f --apply.
- [X] T044 [US3] Assert os.rename (or equivalent) is the only mutating call; no shutil/copytree/remove in the apply path (static or runtime check).

### Implementation for User Story 3

- [X] T045 [US3] Complete `quarantine(...)` and integrate into `run_gc(..., apply=True)`: only when BOTH filter and apply: resolve unique managed (error on 0/ambig/multi per contracts), run safety, compute dest, mkdir parents for dated dir (after safety), os.rename, record QuarantineOperation, print result. On any error before rename: no side effects. On cross-fs etc: specific message + exit 1. Update GCReport with operations + errors.
- [X] T046 [US3] Wire apply path + gates in cli.py main()/cmd path: if command=="gc":
  - if getattr(args, 'apply', False) and not (filter or gc_filter): print("error: --apply requires -f NAME", file=sys.stderr); sys.exit(1)
  - else call run_gc(..., apply=...)
  Match exact strings from contracts/README.md.
- [X] T047 [US3] Update dispatch to print apply success/failure and return proper exit code from main (0 success apply, 1 on errors).
- [X] T048 [US3] Verify quickstart Scenarios 3-7 (quarantine, ambiguous reject, multi-match, repeated, missing) using temp dir + wrapper script.
- [X] T049 [US3] `uv run pytest .../test_gc.py -q -k "us3 or apply or quarantine or collision or symlink" --tb=line` passes.
- [X] T050 [US3] Confirm in code: GC never walks/prunes .comfygo_trash (FR-007).

**Checkpoint**: US2 + US3 complete and independent. Safe explicit-target quarantine works. MVP + P2 delivered.

---

## Phase 6: User Story 4 - Ambiguous Folder Reporting (Priority: P2)

**Goal**: Ambiguous folders (no marker) are always reported under "Ambiguous" and are never moved even under --apply. Reserved/hidden/source-symlink are skipped per rules (FR-003/FR-004). Users understand why something is ineligible.

**Independent Test**: Create no-marker folder; `gc` (and filtered) lists it under Ambiguous; `gc -f <ambig> --apply` errors with "not managed by comfygo".

### Tests for User Story 4

- [X] T051 [P] [US4] Ambiguous listed correctly (covered in US2 but dedicated): filter on ambiguous name reports only under Ambiguous section.
- [X] T052 [P] [US4] Reserved + hidden never appear in ambiguous or managed output (silent skip).
- [X] T053 [P] [US4] Ambiguous targeted with --apply is rejected with exact contract message (T035).
- [X] T054 [US4] Source symlink surfaced appropriately in Warnings when relevant (or as skipped).

### Implementation / Integration for User Story 4

- [X] T055 [US4] Ensure scan logic (T007) + report (T025) correctly classify and output ambiguous vs. skipped vs. managed. No additional mutation paths.
- [X] T056 [US4] Verify all ambiguous-related quickstart + spec acceptance scenarios pass.
- [X] T057 [US4] Add any missing report/warning details for skipped reasons if contracts require visibility.

**Checkpoint**: All four user stories covered. Ambiguous behavior explicit and safe.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Docs, final verification, cleanup, full suite, .gitignore, constitution compliance. Run after desired stories.

- [X] T058 [P] Update `docs/model-library.md`: add "GC Command" section after reconcile. Include: dry-run example (exact format), `comfygo models gc -f NAME --apply` example, `.comfygo_trash/<date>/` layout + manual restore instructions, safety note ("marker means known by comfygo, **not** disposable; requires explicit -f --apply"). Per decomposed 7.x.
- [X] T059 [P] Review gc.py + cli changes: uv-first (only in docs/tests), no hard-coded model paths (use --models-dir / folder_paths), reuse validate_path_segment + reserved policy, no direct python/pip in added code. Fix any violations.
- [X] T060 Run full test suite with uv: `UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line`. Must pass (old + new gc tests).
- [X] T061 Run `git diff --check` (no whitespace errors on changed files).
- [X] T062 Clean repo __pycache__: `find . -path '*/__pycache__/*' -delete; find . -type d -name __pycache__ -exec rm -rf {} +` (target gc related + tests). Confirm none committed for new files.
- [X] T063 Verify/update `.gitignore` (repo root) contains patterns for `.comfygo_trash/` (and perhaps test temps). Add if missing. Never commit trash contents.
- [X] T064 Confirm all safety checklist items in `specs/002-model-gc/checklists/safety.md` are [x] (23 items). Re-review against final code if any drift. (requirements.md already complete.)
- [X] T065 Run quickstart.md end-to-end validation scenarios 1-7 in a fresh temp dir (using the wrapper). Capture output matches expectations.
- [X] T066 Optional: run /speckit-analyze (or equivalent) to confirm cross-artifact consistency post-impl.
- [X] T067 (if needed) Promote any remaining atomic decomp subs from plan.md into explicit tasks or close them via verification here.

**Checkpoint**: Baseline implementation through T067 is complete. Final readiness is established only after Phase 8 T068-T079 and final verification are closed.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: None — start immediately.
- **Foundational (Phase 2)**: Depends on Setup. **BLOCKS** all user stories (scan/safety must exist).
- **US1 (Phase 3)**: Can run after Setup (mostly verification of pre-existing).
- **US2 (Phase 4, MVP)**: Depends on Foundational. Dry-run uses scan + classify + report.
- **US3 (Phase 5)**: Depends on US2 + Foundational (quarantine reuses scan + safety).
- **US4 (Phase 6)**: Depends on US2 (ambiguous is part of report) + scan.
- **Polish (Phase 7)**: Depends on US2/US3 (at minimum) + desired stories.

### User Story Dependencies
- US1 (P1, pre-existing): Independent of new GC code.
- US2 (P1): Independent once foundational ready.
- US3 (P2): Requires US2 infrastructure.
- US4 (P2): Primarily covered by US2 report logic.

### Within Each User Story
- Tests written + FAIL first (TDD).
- Scan + detect_markers before report formatting.
- Safety + collision before quarantine apply.
- Core logic before CLI wiring.
- Wiring + format before quickstart verification.
- Story checkpoint before next priority.

### Parallel Opportunities
- All Setup T001-T004 [P] capable.
- T005-T009 foundational pieces (data classes, detect, scan, safety, collision) — many parallelizable; T010 depends on prior.
- US2 tests T015-T024 parallel.
- US3 tests T031-T044 parallel.
- Docs T058 + .gitignore T063 + some verify can parallelize with late US3.
- US1 verify parallel with early phases.
- Different stories by different agents once Foundational done.

---

## Parallel Example: User Story 2 (MVP)

```bash
# Tests (launch together):
Task: "T015 [P] [US2] Test dry-run managed folder..."
Task: "T017 [P] [US2] Test ambiguous..."
Task: "T020 [P] [US2] Test reserved/hidden..."

# Impl (after tests written):
Task: "T025 [US2] Implement build_report + format_report in gc.py"
Task: "T026 [US2] Implement run_gc dry-run path"
Task: "T027 [US2] Wire gc dispatch in cli.py"
```

---

## Implementation Strategy

### MVP First (User Story 2 Only)
1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational (raw scan + safety critical).
3. Complete Phase 3 US1 verification (quick).
4. Complete Phase 4 User Story 2 (dry-run reporting + filter).
5. **STOP and VALIDATE**:
   - All US2 tests pass.
   - quickstart Scenarios 1+2.
   - Manual: `scripts/comfygo-models.sh gc --models-dir /tmp/testroot` shows correct report, no trash created.
6. Demo: users safely inspect what comfygo "knows".

### Incremental Delivery
1. Setup + Foundational → base primitives.
2. US1 verify + US2 (dry-run) → **MVP!** — inspection only.
3. US3 (explicit apply quarantine) → safe destructive action with all guards.
4. US4 (ambiguous explicit) → complete reporting.
5. Polish → docs, tests, cleanup, release.
6. Each increment adds value; previous stories remain independently testable.

### Parallel Team / Low-Tier Agent Strategy
- Use the current "Low-Tier Agent Assignment Notes" in plan.md for
  coordination. This tasks.md file remains the canonical actionable list:
  - Setup → T001-T004.
  - Foundational safety → T005-T010.
  - US1 verification → T011-T014.
  - US2 dry-run MVP → T015-T030.
  - US3 explicit apply → T031-T050.
  - US4 ambiguous reporting → T051-T057.
  - Polish and verification → T058-T067.
  - Phase 8 convergence remediation → T068-T079.
  - Phase 9 convergence remediation → T080.
  - Phase 10 requirements quality closure → T081-T082.
- Lowest-tier agents can take single atomic sub (e.g. "implement detect_markers exactly per T006", "add one specific test case").
- After Foundational, multiple agents on separate US test+impl tracks.

---

## Notes
- [P] = different files or no dep; safe to parallel.
- Story labels for traceability to spec user stories.
- Every task includes concrete file + acceptance criteria so lowest-tier agents (or implement) can execute without extra context.
- Always use temp dirs for validation (never real models).
- Re-run full `uv run pytest` + quickstart before claiming checkpoints.
- If uv not present: fail task with "install uv" per constitution.
- After impl: consider running `/speckit-converge` + `/speckit-analyze` to confirm zero remaining gaps.
- US1 phase ensures the "gc umbrella" does not silently drop prior reconcile responsibilities.

---

## Phase 6 (Historical Convergence) Note
Previous convergence (pre-regen) identified 9 gaps (no gc.py, no cli gc,
no test_gc.py, wrapper partial, raw-iterdir unmet, safety absent, docs,
polish, checklists). All are now represented by explicit tasks above
(T001-T079 range, including Phase 8 convergence remediation). Do not use
obsolete pre-regeneration task IDs for assignment. This tasks.md is the
canonical actionable list.

## Phase 8: Convergence

- [X] T068 Verified no machine-local absolute path examples remain in feature artifacts/docs/scripts checked by the public-repo hygiene scan.
- [X] T069 Reused the scanner reserved-folder policy for GC skip decisions case-insensitively, with tests for omitted reserved categories such as `ipadapter` so reserved folders are never managed or quarantinable per FR-004.
- [X] T070 Refactored `custom_nodes/comfygo_model_registry/cli.py` so the `gc` command dispatches to `gc.run_gc(models_dir, filter_str, apply)` before building legacy roots or calling `scanner.scan_models()`, with a regression test that `scanner.scan_models` is not called for GC per FR-015.
- [X] T071 Surfaced source-symlink skipped entries as contract warnings in dry-run/filter/apply output, including the `warning: Refusing to quarantine symlinked folder '<path>'` case and exit behavior per FR-003 and FR-014.
- [X] T072 Hardened `quarantine()` so the mutating primitive independently refuses non-top-level sources and source symlinks before creating trash directories or calling `os.rename()` per FR-005 and FR-014.
- [X] T073 Aligned GC data classes with `data-model.md` by adding `QuarantineOperation`, `GCReport.operations`, and `GCReport.selected_target`, and recording apply outcomes through those fields per data-model.
- [X] T074 Recorded and printed a destination-collision warning when quarantine uses a numeric suffix, and asserted the warning in tests per FR-011.
- [X] T075 Made filtered dry-run no-match return/report an error so CLI exits 1 for `gc -f NAME` with no visible managed or ambiguous matches per contracts/README.md.
- [X] T076 Added missing GC CLI and wrapper integration tests covering temp-dir dry-run, wrapper `gc --models-dir`, apply-without-filter, raw-scan dispatch, and quickstart validation paths per T004, T028, and T065.
- [X] T077 Added the missing `docs/model-library.md` GC Command section with dry-run output, explicit `-f NAME --apply`, `.comfygo_trash/<date>/` restore guidance, and the marker-is-not-disposable safety note per T058.
- [X] T078 Cleaned trailing whitespace in feature task/spec artifacts and verified whitespace checks include untracked feature files before claiming T061 complete per T061.
- [X] T079 Add GC dry-run performance smoke coverage for SC-012: create approximately 100 top-level temp model folders, run `gc.run_gc()` or CLI dry-run against that temp root, assert completion under 1 second, assert no `.comfygo_trash/` is created, and include the test in `custom_nodes/comfygo_model_registry/tests/test_gc.py` or equivalent focused test coverage.

## Phase 9: Convergence

- [X] T080 Handle unsafe quarantine path segment validation as a controlled GC error in `custom_nodes/comfygo_model_registry/gc.py` and add regression coverage in `custom_nodes/comfygo_model_registry/tests/test_gc.py`, plus CLI/wrapper coverage in `custom_nodes/comfygo_model_registry/tests/test_cli.py` or `custom_nodes/comfygo_model_registry/tests/test_wrapper.py`: applying to a managed folder whose name fails `models.validate_path_segment()` must exit 1 without traceback, leave the source untouched, create no `.comfygo_trash/`, and report `error: Unsafe path segment: '<name>'; no files changed` through both direct GC logic and the user-facing `scripts/comfygo-models.sh gc --models-dir <tmp> -f '~UnsafeModel' --apply` path per FR-005/T008 (partial)

## Phase 10: Requirements Quality Closure

- [X] T081 Align unsafe-folder-name wording in `specs/002-model-gc/spec.md` and `specs/002-model-gc/quickstart.md` with `specs/002-model-gc/contracts/README.md` and T080: explicitly include exit 1, no traceback, source unchanged, no `.comfygo_trash/` creation, no GC normalization to `<kind>-NNN`, and the exact message `error: Unsafe path segment: '<name>'; no files changed`
- [X] T082 Review `specs/002-model-gc/checklists/normalization-boundary.md` against `specs/002-model-gc/spec.md`, `specs/002-model-gc/plan.md`, `specs/002-model-gc/research.md`, `specs/002-model-gc/data-model.md`, `specs/002-model-gc/contracts/README.md`, `specs/002-model-gc/quickstart.md`, and `specs/002-model-gc/tasks.md`; add inline notes for any residual requirement-quality findings, then mark CHK001-CHK022 checked only when every item has supporting artifact evidence
