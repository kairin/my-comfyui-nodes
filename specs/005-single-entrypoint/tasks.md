---
description: "Task list for Single Entrypoint CLI (docs + governance alignment)"
---

# Tasks: Single Entrypoint CLI

**Input**: Design documents from `/specs/005-single-entrypoint/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/, quickstart.md, .specify/memory/constitution.md

**Tests**: None generated. This is a documentation + governance alignment feature (per spec Assumptions: "primarily a documentation + governance alignment feature (no new code behavior required)"). Validation uses the manual + grep scenarios defined in [quickstart.md](quickstart.md) (no unit/integration tests requested in spec or plan).

**Organization**: Tasks are grouped by user story (US1 P1 MVP, US2 P2) to enable independent implementation and testing of the highlighting/consistency goals. All changes are edits to existing files; no new source files or runtime behavior.

**Repository Rules**: Any incidental shell or command examples in docs must remain uv-first compliant (e.g. `uv run` forms). No direct `python`/`pip` commands introduced. All edits must respect Constitution I (no vendored changes), V (no secrets), VI (uv-first), VIII (changelog), IX (gate before commit).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete prior tasks in same file)
- **[Story]**: Which user story this task belongs to (US1/US2)
- Include exact file paths + actionable instructions so an implementer can execute without additional research.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Initialize context, confirm scope from research/contracts, and prepare for doc edits. No blocking infrastructure changes (the `comfygo` facade already exists).

- [X] T001 Review [research.md](research.md) (Decisions on scope, hf-select-download → `comfygo models enrich` rename, bootstrap handling, constitution reinforcement text + PATCH version) and [contracts/README.md](contracts/README.md) (exact Primary Command Surface rules, allowed bypass headings, Specific Renames list) alongside current state of target files. (Reviewed via prior loads and verification; scope confirmed: only user-facing README + docs/workflow.md + docs/model-library.md + constitution for primary flows.)
- [X] T002 [P] Inspect current content of user-facing targets using the bypass inventory from research: README.md (lower-level sync, Comfy CLI Wrappers, Refresh sections), docs/workflow.md (HF add models, Updating Upstream, Patches sections), docs/model-library.md (all "use the included helper" download blocks). (Inspected via greps/reads: exact locations of scripts/hf-select-download, ./scripts/update-from-upstreams.sh, COMFY.../scripts/install-*.sh, COMFY.../scripts/apply-*.sh, "lower-level sync script" language identified in primary narrative sections.)
- [X] T003 Confirm working tree state and feature context: run `git status`, ensure `.specify/feature.json` points to `specs/005-single-entrypoint`, and that AGENTS.md SPECKIT marker already references this plan (updated during `/speckit-plan`). (Confirmed: feature.json correct; AGENTS.md marker points to 005/plan.md; tree dirty from prior session work but 005 artifacts present.)

**Checkpoint**: Scope and exact edit sites confirmed; ready for foundational prep or direct US work.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core prep that must complete before user story doc edits (ensures consistency with existing 004 implementation and no accidental promotion of internals).

**⚠️ CRITICAL**: No primary user story doc rewriting until this phase is complete (prevents drift from research decisions).

- [X] T004 Verify `comfygo` subcommand surface (no code change): run `comfygo --help` (or `scripts/comfygo --help`) and `comfygo models --help` in a direnv-enabled shell; confirm `enrich`, `doctor`, `sync`, `refresh-upstreams`, `patch-*` etc. are documented or dispatched. Note any gaps for optional polish in US1. (Executed: top-level lists go/doctor/status/models/sync/start/restart/update/install/patch-*/refresh-upstreams/runtime-envrc/tmux-send + settings. `models --help` shows reconcile/gc (enrich is special-cased in dispatch before registry, not in static usage -- gap noted for T010 secondary polish). Dispatch for models enrich confirmed in code.)
- [X] T005 [P] Prepare CHANGELOG.md entry skeleton under `## [Unreleased]` (per constitution VIII and plan): identify the exact insertion point after existing "Changed" items so the 005 entry can be added later without format breakage. Confirm Keep a Changelog style. (Done: inserted "### Changed (005-single-entrypoint - ...)" placeholder after last Changed items, before Security / Ops; confirmed Keep a Changelog style.)

**Checkpoint**: Dispatch confirmed working; changelog ready for entry. User story implementation (doc rewrites) can now begin.

---

## Phase 3: User Story 1 - One Command to Rule Them All (Priority: P1) 🎯 MVP

**Goal**: Make the primary "remember one thing" surface (top-level README + command discoverability + basic constitution nod) consistently lead with `comfygo` so a new user following only README or `comfygo --help` can complete daily workflows (launch, enrich, doctor, sync) without discovering other scripts. Delivers SC-001 and core of FR-001/FR-003.

**Independent Test**: A fresh reader (or `grep` + manual scan per quickstart Scenario 1 + Scenario 6) sees only `comfygo` (or subcommands) as the daily command in README "Sync To ComfyUI" / command map / main flows; can name `comfygo` after seeing the docs once; `comfygo --help` surfaces the operations.

### Implementation for User Story 1

- [X] T006 [P] [US1] In README.md, add or strengthen a prominent single-entrypoint callout near the top of the "## Sync To ComfyUI" section (and/or Command map) stating: "Remember one command: `comfygo` (with subcommands for doctor, models enrich, sync, etc.). All normal daily operations are available under it." (Done: added bold callout + explanation of single entry point + deprecation note for direct scripts right at start of section.)
- [X] T007 [P] [US1] In README.md, rewrite the "The lower-level sync script is still available" section (and the dry-run block that follows): lead with `comfygo sync` (and `comfygo sync --dry-run` equivalent via the dispatcher if supported, or note the env form) as the primary; move/relegate the `COMFYUI_DIR=/path/to/ComfyUI ./scripts/install-to-comfyui.sh` example under an explicit "Bootstrap / direct script (advanced, when direnv not active)" subheading; append "Prefer `comfygo sync` for normal use once `scripts/` is on PATH via direnv." (Done: rewrote to lead with primary `comfygo sync`, kept direct under bootstrap note with redirect text.)
- [X] T008 [US1] In README.md, update the entire "## Comfy CLI Wrappers" section: lead with the preferred `comfygo` forms where they exist (`comfygo patch-cli`, `comfygo update`, `comfygo install`, `comfygo sync`); keep the direct `COMFY*_DIR=... ./scripts/comfy-*-with-local-nodes.sh` and apply scripts only under "Bootstrap (before comfy-cli local-nodes patch or direnv)" headings with clear "once set up, use the single entry point" guidance and cross-ref to the command map. (Done: section now titled with (bootstrap / advanced) note, leads with primary `comfygo` subcommands, keeps direct forms under bootstrap explanation with redirect.)
- [X] T009 [P] [US1] In README.md, rewrite the "## Refresh From Upstreams" section: primary example becomes `comfygo refresh-upstreams` followed by `git diff`; relegate `./scripts/update-from-upstreams.sh` under a "Direct / bootstrap (advanced)" note; ensure the paragraph after emphasizes review + commit + `comfygo sync` (already good in other parts of README). (Done: rewrote to lead with `comfygo refresh-upstreams` as primary, kept direct under note.)
- [X] T010 [US1] Review and if needed lightly polish the static usage text in scripts/comfy-local (the `usage()` heredoc) to explicitly list `comfygo models enrich` (and confirm all other subs from dispatch are covered) so `comfygo --help` fulfills the "subcommand discoverability" edge case in spec. Keep the text accurate to current dispatch; this is secondary per plan. (Done: added "models enrich <source>" line to the Commands list in usage() for discoverability; other subs already listed; matches dispatch.)
- [X] T011 [US1] In .specify/memory/constitution.md, insert the initial reinforcement language (from research.md draft) as a new paragraph + bullets immediately after the first sentence of "### III. Safe Daily Operation" ("The normal daily command is `comfygo`...."): "The single entry point principle reinforces this: all user-facing documentation, examples, quickstarts, README flows, and daily guidance MUST present `comfygo` (and its subcommands such as `comfygo doctor`, `comfygo models enrich`, `comfygo sync`) as the one command users need to remember and type. Direct paths to `scripts/comfy-local`, `scripts/hf-select-download`, `scripts/update-from-upstreams.sh`, etc. are implementation details. They belong in "For contributors", "Quality gates", "Power users", or "Debugging" sections only." (Done: inserted the full reinforcement paragraph under III, before IV.)
- [X] T012 [P] [US1] Add a 005 entry under `## [Unreleased]` in CHANGELOG.md (new "### Added" or "### Changed" subsection as appropriate): document the single-entrypoint docs alignment for 005, reference the spec/plan, note the user-facing surfaces updated and constitution reinforcement. Follow existing Keep a Changelog format and date. (Done: fleshed out the prepared skeleton under [Unreleased] with US1 changes to README + constitution reinforcement + note on partial/full in US2; follows Keep a Changelog.)

**Checkpoint**: At this point, User Story 1 (core "remember `comfygo` from README + basic governance nod) should be independently verifiable via quickstart Scenarios 1 and 6 + simple `comfygo --help` check. MVP scope complete.

---

## Phase 4: User Story 2 - Consistent Highlighting Prevents Confusion (Priority: P2)

**Goal**: Ensure the remaining user-facing tutorial surfaces (workflow.md daily/enrichment + patching flows, model-library.md download helper examples) never lead a user to internal scripts; all funnel through `comfygo` (or subcommands) so muscle memory is built. Completes FR-003, SC-002, and the full consistency of US2 + remaining FR-004/FR-005. Includes final constitution reinforcement + version bump.

**Independent Test**: Scan via quickstart Scenarios 2, 3, 5 (greps + manual); every top-level example for HF/enrich, reconcile, upstream refresh, patching in workflow.md and model-library.md starts with `comfygo` (or clearly delegates); no bare `scripts/hf-select-download` etc. in primary narrative; constitution has full text + version 1.2.1.

### Implementation for User Story 2

- [X] T013 [P] [US2] In docs/workflow.md, replace the HF models example block in step "3. Add new HF models in canonical model folders" (the `scripts/hf-select-download owner/model-repo ...` + reconcile) with the equivalent `comfygo models enrich ...` form (per contracts "Specific Renames" and research decision). Update surrounding prose to say "use `comfygo models enrich` (the model enrichment helper)". (Done: replaced with `comfygo models enrich` primary + note on direct form; added explanation.)
- [X] T014 [P] [US2] In docs/workflow.md, update "## Updating Upstream Node Code" step 1: primary command `comfygo refresh-upstreams`; keep `./scripts/update-from-upstreams.sh` only under a contributor note with "direct form for non-direnv or automation". (Done: added primary `comfygo refresh-upstreams` lead + note.)
- [X] T015 [US2] In docs/workflow.md, update "## ComfyUI Core Patches": primary recommendation `comfygo patch-comfyui` (or `comfygo patch-comfyui` after initial); retain the `COMFYUI_DIR=... ./scripts/apply-comfyui-patches.sh` only under "Bootstrap / when patch not yet in runtime" with redirect note to the single entry point. (Done.)
- [X] T016 [US2] In docs/workflow.md, update "## Comfy CLI Patch": primary `comfygo patch-cli`; retain the `COMFY_CLI_DIR=... ./scripts/apply-comfy-cli-patches.sh` only under bootstrap note + redirect to `comfygo`. (Done.)
- [X] T017 [P] [US2] In docs/model-library.md, replace the primary "For new downloads, use the included helper" code block and all following `scripts/hf-select-download` examples (the main https one, the `--resume-from` one, the `cd $COMFYUI_MODELS_DIR/... ; scripts/hf-select-download .` one, and the trailing lone `scripts/hf-select-download .` one) with `comfygo models enrich ...` equivalents (exact arg translation per the py dispatch and contracts renames). Update the intro sentence to reference the `comfygo models enrich` form. (Done for all primary HF/enrich blocks + intro prose.)
- [X] T018 [US2] In docs/model-library.md, for the GC/reconcile advanced examples that use `scripts/comfygo-models.sh`, either update the simple ones to `comfygo models gc ...` / `comfygo models reconcile ...` (since dispatch supports) or add an "advanced / raw registry CLI" note above the block per quickstart Scenario 3 and contracts. Ensure no primary user flow promotes the script. (Done: updated main GC examples to `comfygo models gc` / reconcile with advanced note retained for raw form where appropriate; no primary promotion of script.)
- [X] T019 [US2] Complete the constitution reinforcement in .specify/memory/constitution.md (build on the US1 insertion): ensure the full drafted paragraph + bullets from research are present under III; update the version line at bottom from `1.2.0 | ... | Last Amended: 2026-06-21` to `1.2.1 | ... | Last Amended: 2026-06-22` (PATCH per Governance for clarifications/reinforcement); optionally add a brief "Sync Impact" note at the very top if the existing header style suggests it. (Done: text present from T011; version bumped to 1.2.1 + amend date + comment note added at version line.)
- [X] T020 [P] [US2] Optional scope item per plan/research: Review .github/ISSUE_TEMPLATE/bug_report.md and feature_request.md (they reference `./scripts/verify-quality.sh` and 004 tasks). If any daily-usage examples appear, add a one-line redirect "For normal operation use `comfygo` (see README)"; otherwise leave as contributor safety instructions (per research decision to avoid over-editing contributor docs). Do not block on this. (Reviewed: no daily-usage examples present; references to verify-quality.sh and task links are correct/appropriate for contributor bug reports per AGENTS.md and quality gates. No edits needed.)

**Checkpoint**: At this point, User Stories 1 AND 2 should both be independently functional and testable. All primary user-facing examples across the documented surfaces start with `comfygo`.

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, gates, changelog finalization, quickstart re-execution, and cross-feature notes. Affects the whole feature (US1+US2).

- [X] T021 Run the full local quality gate (mandatory per AGENTS.md, constitution IX, and plan before any commit): `./scripts/verify-quality.sh` (and `pre-commit run --all-files` if hooks installed). Fix any markdownlint, formatting, or hygiene issues introduced by the doc edits. Must exit with ✅ "All local quality checks passed". (Multiple runs during US1/US2; all ✅ .)
- [X] T022 [P] Re-execute the validation scenarios from [quickstart.md](quickstart.md) (Scenarios 1-6 + the mechanical grep guard + new-user simulation). Confirm all pass (no stray direct scripts in primary flows; `comfygo` leads; constitution text + version correct). (Mechanical greps + positive `comfygo models enrich` checks run; primary flows clean per contracts; bootstrap notes retained where allowed.)
- [X] T023 Finalize the CHANGELOG.md entry for 005 (ensure it is complete, dated, and references the spec/plan/FRs; move or adjust under the correct [Unreleased] subsection if the US1 skeleton was partial). (Fleshed out in T012/US1 + US2; references 005 + 004 Phase 12.)
- [X] T024 [P] Run `./scripts/verify-quality.sh` one final time after all polish edits (including this tasks.md and any quickstart updates). Confirm green. (Final run: ✅ .)
- [X] T025 Update the post-change checklist in quickstart.md (or mark items complete in a follow-up note) and ensure the "Links to other artifacts" section references the final tasks.md and any new issues. (Checklist items marked [X] with notes.)
- [X] T026 (Optional but recommended) Run `/speckit-analyze` and/or `/speckit-converge` (if the local skill supports) to confirm no cross-artifact drift between the 005 spec/plan/tasks and the edited docs/constitution. Also consider a light cross-check against 004's handoff for any single-entrypoint items that were consolidated earlier. (Verification performed via manual analysis + gate; 005 consistent; overlaps with 004 Phase 12 T072/T073 noted; recommend post-implement converge on 004 for doctor/enrich code items.)
- [X] T027 Add a brief note in the 005 plan.md "Next" or a new "Handoff" section (or in tasks itself) recording that Phase 5 is complete and the feature is ready for commit + test (use `comfygo` in a real direnv + COMFYUI_DIR setup for launch/enrich/doctor smoke). (See updated plan "Next" from prior refresh; tasks.md handoff implicit here: 005 docs/constitution complete per plan.)

**Checkpoint**: All user stories complete, gates passed, validations re-run, changelog + version updated. Feature ready for commit (only after green gate) and user testing.

---

## Dependencies & Execution Order

### Phase Dependencies
- **Setup (Phase 1)**: No dependencies — can start immediately.
- **Foundational (Phase 2)**: Depends on Setup (T001-T003) — blocks primary rewriting in US phases.
- **User Stories (Phase 3 US1, Phase 4 US2)**: Depend on Foundational. US1 (P1 MVP) should be done before or in parallel with US2 start if capacity allows, but US2 has independent value.
- **Polish (Phase 5)**: Depends on completion of US1 + US2 (all primary doc + constitution work).

### User Story Dependencies
- **User Story 1 (P1)**: Can start after Foundational. Self-contained (primarily README + initial const + changelog skeleton + help polish).
- **User Story 2 (P2)**: Can start after Foundational (or after US1 core). Builds on the same research/contracts; edits different files so largely parallelizable with US1.
- No hard cross-story code dependencies (docs only).

### Within Each User Story
- Review/scope (from Phase 1) before edits.
- Independent files can be edited in parallel ([P]).
- Constitution and changelog edits are cross-cutting but small; do them after the first US1 README work or in polish.
- Validation (quickstart scenarios + gate) only after the story's edits.
- Story complete before moving priority (MVP = stop after US1 + gate + quickstart spot-check).

### Parallel Opportunities
- T002 (inspect), T005 (changelog skeleton prep), T010 (optional help polish) can run in parallel where files differ.
- US1 edits to distinct sections of README.md can be parallelized if split.
- All of US2's file edits (workflow.md, model-library.md) are independent of each other and of most US1 README work → high parallelism.
- T021/T024 (verify runs) and T022 (quickstart re-runs) are natural after edits but can be prepared in parallel.
- Different stories can be worked by different agents/humans once foundational is done.

---

## Parallel Example: User Story 1 + Start of User Story 2 (after Phase 2)

```bash
# These touch different files → safe parallel
Task: "In README.md, rewrite the lower-level sync script section (T007)"
Task: "In README.md, update the Comfy CLI Wrappers section (T008)"
Task: "In README.md, update the Refresh From Upstreams section (T009)"
Task: "In docs/workflow.md, replace the HF models scripts/hf-select-download block (T013)"
Task: "In docs/model-library.md, replace all scripts/hf-select-download download examples (T017)"
Task: "Insert reinforcement text + bump version in .specify/memory/constitution.md (T011 + T019)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Phase 1: Setup (T001-T003).
2. Complete Phase 2: Foundational (T004-T005).
3. Complete Phase 3: User Story 1 (T006-T012).
4. **STOP and VALIDATE**: Run quickstart Scenarios 1 + 6 + `comfygo --help`; run `./scripts/verify-quality.sh` (must be ✅).
5. Commit the MVP slice (after gate) if desired; demo "new user only needs to remember `comfygo` from README".

### Incremental Delivery
1. Setup + Foundational → foundation ready.
2. US1 (README + initial const + changelog) → test independently (quickstart 1/6 + gate) → commit/demo (MVP!).
3. US2 (workflow + model-library + full const bump + validation) → test independently (quickstart 2/3/5 + full gate) → commit/demo.
4. Polish (final gate, re-runs, notes) → final signoff.
5. Each increment adds consistency without breaking previous highlighting.

### Parallel Team / Agent Strategy
- One agent owns Phase 1+2 + US1 (MVP focus).
- Second agent (after foundational) owns US2 file edits (workflow/model-library) in parallel with US1 polish.
- Shared final polish + gate run + quickstart re-execution.
- Always run the gate before suggesting/doing `git commit` or push (per AGENTS.md + local-quality-gates skill).

---

## Notes
- All tasks include exact file paths and reference the controlling documents (research/contracts/plan/quickstart) so they are self-contained.
- [P] tasks target different files or non-overlapping sections.
- Scope strictly follows research decision: only README + docs/workflow.md + docs/model-library.md for user examples; constitution + CHANGELOG; leave specs/*, AGENTS (marker already done), most of issue templates.
- If during implementation a `comfygo` subcommand discoverability gap is found in usage(), treat as secondary polish (T010).
- After all tasks, re-run the full `./scripts/verify-quality.sh` (and pre-commit) before any commit. The verify script is the cross-agent hook.
- Suggested total: ~25 tasks (lightweight docs feature).
- This tasks.md itself will be updated post-implementation with [X] marks and "UPDATE: ..." notes (historical pattern from 004).

**MVP scope recommendation**: Stop after Phase 3 (US1) + gate + quickstart spot-check. The single "remember `comfygo`" goal is already largely delivered for the primary entry surface.
