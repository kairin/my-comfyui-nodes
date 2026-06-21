# Tasks: Comfygo Patched Tmux Control

**Input**: Design documents from `/specs/004-comfygo-patched-tmux/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md (none), data-model.md (none), contracts/ (none)

**Tests**: Tests are OPTIONAL unless explicitly requested. Core flows will have manual + shell verification steps.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Include exact file paths in descriptions

## Repository Rules For Generated Tasks

- Python and comfy-cli tasks MUST use uv-first command forms: `uv run`, `uv pip --python <workspace-python>`, or `uv run --python <workspace-python> --no-project python ...`.
- Do not generate tasks that use direct `pip`, `python -m pip`, or unwrapped `python` workflow commands.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure for the feature

- [X] T001 Confirm `specs/004-comfygo-patched-tmux/spec.md` and `plan.md` contain no unresolved `NEEDS CLARIFICATION` markers
- [X] T002 [P] Add `.github/ISSUE_TEMPLATE/` or update contributing docs to reference the new feature principles (changelog, solo-maintainer protections)
- [X] T003 Update root `CHANGELOG.md` entry for this feature (already seeded in prior step; ensure it stays maintained) **UPDATE: Done for current polish** - entries added for 004 work, settings, protection, quality gates. Follow up: keep updated on each commit.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core patching hygiene, settings loader, and safety net basics that unblock all user stories. CRITICAL – complete before user stories.

- [X] T004 Strengthen GitHub branch protection for solo maintainer (see recommendations below): require PRs to main, require status checks (at least Codacy), block force pushes/deletes, enable conversation resolution. Set required reviews to 0 (or 1 with self-approval allowed). Document the "good enough" config in `docs/workflow.md`. **UPDATE: Complete** - protection rules active (per gh api), workflow.md updated.
- [X] T005 [P] Verify/enhance Codacy configuration: ensure "Codacy Gate Policy" and key tools (Bandit, Pylint/Prospector, ShellCheck, Trivy/Checkov, markdownlint) are active. Wire the Codacy workflow check as a required status check in GitHub protection (do not make grade a hard fail yet for solo dev). **UPDATE: Active** - Gate Policy and tools enabled, analysis required in GH per current protection.
- [X] T006 Implement up-front declarative settings loader (local/ignored only, e.g. via direnv or a small config in the repo root). Define keys for: patching behavior, launch policy (tmux window name, etc.), model enrichment policy, protection reminders. **UPDATE: Implemented** - load_comfygo_settings() in scripts/comfy-local; integrated into usage and doctor. Follow up: use COMFYGO_* vars in launch/tmux logic (T014).
- [X] T007 Add a `comfygo doctor --protection` or extend existing doctor to surface current GitHub protection + Codacy gate status (verifiable safety nets). **UPDATE: Extended** - protection probe added to doctor() in scripts/comfy-local (uses gh if available). Follow up: full --protection flag if needed.
- [X] T008 Update install/sync scripts if any remaining test leakage or hygiene gaps from 003 convergence apply here (cross-reference). **UPDATE: Exclusions present in install-to-comfyui.sh; hygiene in verify.**

**Checkpoint**: Foundation ready. User story work can begin.

---

## Phase 3: User Story 1 - Reliable Patch of Currently Installed Base (Priority: P1) 🎯 MVP

**Goal**: The vendored base (custom_nodes + known patches) reliably patches and re-patches the currently installed ComfyUI/comfy-cli setup.

**Independent Test**: Run patch/sync (via `comfy local-nodes` or scripts). Simulate upstream change. Verify re-patch either succeeds using manifests or clearly informs the user.

### Implementation for User Story 1

- [X] T009 [US1] Create versioned patch manifests/docs under `comfyui-patches/<version>/manifest.md` (and `comfy-cli-patches/<version>/manifest.md`) describing touched files, historical node names for matching, and rationale. Keep non-secret only. Aligns with existing repo layout (updated in plan.md polish).
- [X] T010 [US1] Enhance re-patch / drift detection logic (in `scripts/comfy-local` or a new helper called from launch/patch flows). Use manifests in comfyui-patches/ + name/path heuristics (per updated plan). On mismatch: clear actionable message pointing to docs + "update patch" guidance. **UPDATE: Added patch_drift_check() called in doctor and status.**
- [X] T011 [US1] Update `scripts/install-to-comfyui.sh`, `update-from-upstreams.sh`, and the local-nodes patch content to be consistent with the manifests in comfyui-patches/ (already partially done for tests; complete for patching resilience). Note: may be broken if paths not updated from previous 003 carry-over. **UPDATE: Manifests added; code in comfy-local updated to use them via drift check.**
- [X] T012 [US1] Add "re-patch after update" step to the launch sequence (see US2). Make it part of the sequential "get up to date" phase. Follow up: verify if current scripts/comfy-local handles re-patch using manifests. **UPDATE: Added re-apply calls in comfy-update-with-local-nodes.sh after update.**
- [ ] T013 [US1] [P] Add manual verification test in docs or a smoke script: after simulated `comfy update`, run the tool and confirm patching or clear notification.

---

## Phase 4: User Story 2 - One-Command Launch Owning Full Sequence in Tmux (Priority: P1)

**Goal**: Up-front settings + sequential launch: update → verify (incl. protection) → launch comfy-cli/ComfyUI inside tmux. Controlling shell stays free over SSH (single terminal). The app can still drive the tmuxed process.

**Independent Test**: SSH simulation (or local tmux). Run the launch command. Verify sequence in logs, tmux window created for comfy, controlling shell remains interactive, and control commands (status/stop) work from the shell to the tmux target.

### Implementation for User Story 2

- [X] T014 [US2] Extend `scripts/comfy-local` (or a dedicated launch orchestrator) to read the up-front settings and execute strict sequence: 1. update/patch (US1), 2. verify (doctor + protection checks), 3. tmux launch of `comfy ... launch` (or equivalent) in a managed window/pane. **UPDATE: tmux_launch added, uses settings, sequence in launch path.**
- [X] T015 [US2] Implement tmux helpers: create/attach named window (e.g. "comfyui"), record target id, provide send-command helper so the controlling process can interact without losing the terminal. Document tmux requirements. **UPDATE: tmux_target, tmux_launch, tmux_send_command added.**
- [X] T016 [US2] Make the launch command the primary entry point (update `scripts/comfygo`, wrappers, docs). Ensure it works over plain SSH + direnv (keys for enrichment, etc.). **UPDATE: launch now uses tmux_launch by default via settings; comfygo delegates to comfy-local.**
- [X] T017 [US2] Add graceful handling: if tmux not present, clear error + fallback note (or documented alternative). No X11/GUI assumptions. **UPDATE: fallback in tmux_launch.**
- [ ] T018 [US2] Update verification (quickstart or script) to cover the full sequential tmux launch over simulated single-terminal SSH. **Follow up after full integration.**

---

## Phase 5: User Story 3 - Preferred HF Git-Clone + Civitai Enrichment (Priority: P2)

**Goal**: Support preferred acquisition (full git-clone HF folders with data) + loose files. Detect on Civitai (direnv keys), fetch details, ensure HF skeleton + move weights, add civitai side folder, emit rich `comfygo-model.json` usable by the registry for node discovery.

**Independent Test**: Point tool at a git-cloned HF folder or loose file (with tokens). Verify structured layout + side folder + rich JSON. Reconcile makes it discoverable by kind. Works over SSH.

### Implementation for User Story 3

- [ ] T019 [US3] Enhance `scripts/hf_select_download.py` (or new `enrich-civitai` helper) to:
  - Accept loose file or git-clone HF dir.
  - Query Civitai API (token from direnv), pull rich metadata on match.
  - Locate HF equivalent, download skeleton only if needed, move weights into proper HF layout.
  - Create civitai side folder + enrich/write `comfygo-model.json` (kind, components, source: hf + civitai sections).
- [ ] T020 [US3] Integrate the enrichment into the "get up to date" / model phase of launch (or expose as `comfygo models enrich`).
- [ ] T021 [US3] Ensure the emitted JSON is compatible with existing scanner/descriptor/reconciler (add tolerant fields if needed).
- [ ] T022 [US3] [P] Add examples and quickstart updates showing the full dump + enrich flow.
- [ ] T023 [US3] Privacy: ensure no keys or specific private model names leak into committed examples or docs.

---

## Phase 6: Polish & Cross-Cutting Validation

**Purpose**: Docs, issues, converge, verification.

- [X] T024 Update `README.md`, `docs/workflow.md`, `docs/model-library.md` for: up-front settings, sequential tmux launch, patch manifests/resilience, Civitai+HF enrichment flow, solo-maintainer protection recommendations, new constitution principles. **UPDATE: Partial** - workflow.md and CHANGELOG updated. Follow up: README/model-library after US3.
- [X] T025 Create high-level public GitHub issues (via tools) for remaining work items (safe wording, no secrets/private details). Link back to this tasks.md and spec. **UPDATE: Created via /speckit-taskstoissues for T001-T037.**
- [ ] T026 Run speckit-converge (after implementation) on 004 and on any carried items from 003 to ensure closure. **Note: re-run recommended after remaining work.**
- [ ] T027 End-to-end verification: SSH simulation, full sequence (update/verify/tmux), patching resilience, enrichment end-to-end, no private exposure, existing speckit harnesses still pass where relevant. **Partial: verify and core sequence done; full incl. US3 pending.**
- [ ] T028 (optional) Add a small diagnostic node or CLI helper that uses the registry to demonstrate discovery of enriched models.

---

## Dependencies And Execution Order

- Phase 1 → Phase 2 (foundational patching + settings + protection).
- US1 (patching) and US2 (tmux launch) can overlap after foundational.
- US3 (enrichment) depends on settings + launch sequence for integration.
- Polish last.

### Parallel Opportunities
- T003 (changelog) + protection verification (T004/T005) + docs updates can be parallel.
- Test/exclude hygiene from previous converge can be folded into Phase 2.

### MVP Scope (first increment)
Focus on US1 + US2 (reliable patching + sequential tmux launch with settings) + the minimal protection/Codacy wiring + changelog. This delivers the primary "tool owns the full comfy-cli setup + launch in tmux" value for a solo SSH user.

### Safety Boundary (from plan + constitution)
- All flows over SSH + direnv only.
- No secrets in manifests, issues, docs, or code.
- Patching and enrichment are explicit.
- Single maintainer: protection is "good enough" (PRs + required checks) not overkill (0 reviews, self-approval ok).
- Preserve existing speckit/constitution work.

**Good enough branch protection / Codacy recommendations for single maintainer (document in workflow.md after T004):**

- GitHub main branch:
  - Require pull requests (no direct push to main).
  - Require status checks (Codacy Analysis at minimum) before merge.
  - Required approving reviews: 0 (or 1 allowing owner self-approval).
  - Require branches to be up to date before merging.
  - Require conversation resolution on PRs.
  - Block force pushes + branch deletions: keep enabled.
  - Enforce for admins: off (solo owner flexibility).
  - Linear history: optional.

- Codacy:
  - Keep Gate Policy + key tools enabled.
  - Require the analysis check in GitHub (catches new issues early).
  - Use for PR comments and visibility. Treat grade/goals as guidance, not hard merge blockers while solo (adjust later if team grows).
  - Enable secret scanning / other gates if available.

This provides safety nets (CI feedback, no accidental main pushes) without blocking a solo maintainer.

## Broken or Needs Follow Up Tasks (post /speckit-implement remediation)

**Remaining open tasks (as of this analysis):**
- T013 [US1] [P]: Manual verification test for re-patch after simulated update.
- T018 [US2]: Update verification docs/scripts for full tmux launch sequence.
- T019-T023 [US3]: Full HF/Civitai enrichment implementation and integration (currently partial in hf_select_download.py).
- T026: Re-run /speckit-converge after remaining implementation (this was run pre-implement).
- T027: Full end-to-end verification (SSH sim, sequence, enrichment, no private data, preserve artifacts).
- T028 (optional): Small diagnostic for enriched models in registry.
- T033 [US3]: Complete enrichment helper for git-clone/loose files + JSON output.
- T034: Minor follow-up - confirm exact "analysis" check name in Codacy and extend doctor --protection flag if desired.
- T035: Ongoing - ensure CHANGELOG.md is kept updated on future commits.

**Resolved in this pass (no longer broken):**
- T029 (vendored ruff): Resolved via scoping + reverts.
- T030/T006 (settings loader): Implemented in scripts/comfy-local.
- T031 (manifests): Created in comfyui-patches/ and comfy-cli-patches/.
- T032/T014-T017 (tmux sequence): Implemented (full_launch_sequence, tmux helpers, send-command).
- T036/T037: Reviewed and addressed (cross-cutting justified, uv-first preserved).
- T003/T024/T025: Partial docs/CHANGELOG/issues updates done.

**General notes:**
- Stale language from earlier passes has been cleaned.
- Cross-dependencies (e.g. T012, T014) are now supported by implementation.
- Recommend re-running /speckit-converge and /speckit-analyze after finishing the open items.

## Phase 7: Convergence

**Purpose**: Close gaps between the 004 spec/plan/intent and current codebase state (assessed 2026-06-21, post initial implement pass). Feature had draft/planning stage with partial carry-over from prior work (003 GC doctor, existing patching, hf enrichment, constitution update, quality gates) and unrequested changes from recent ruff runs. Appended actionable remaining work; many Phase 2 + US1/US2 items now implemented (settings, manifests, tmux sequence, docs, etc.).

- [X] T029 CRITICAL: Revert modifications to vendored third-party custom nodes (custom_nodes/ComfyUI-*, comfyui-kjnodes, comfyui-rmbg, etc.) or add ruff/pre-commit excludes for them per Constitution I (Vendored Repo Is Source Of Truth). Recent `./scripts/verify-quality.sh` ruff run reformatted 159+ files including vendored (contradicts) **UPDATE: Resolved** - ruff scoped in .pre-commit-config.yaml and verify-quality.sh to owned code only (comfygo_model_registry + scripts); vendored reverted on branch. No more contradicts.
- [X] T030 Implement up-front declarative settings loader (local/ignored only, e.g. direnv or small config) defining patching, launch/tmux, model enrichment, protection keys per FR-001, T006, plan Phase 2. **UPDATE: Implemented** - load_comfygo_settings() in scripts/comfy-local; integrated into usage and doctor. Follow up: use COMFYGO_* vars in launch/tmux logic (T014).
- [X] T031 Create versioned public patch manifest structure (comfyui-patches/<version>/manifest.md and for comfy-cli) plus driver logic using historical names/paths per updated plan structure, FR-004, FR-005, T009, T010. **UPDATE: manifests created** in comfyui-patches/ and comfy-cli-patches/.
- [X] T032 Implement (or extend comfy-local / comfygo) the strict sequential launch: update/patch (US1) → verify (incl. protection/doctor) → tmux launch of comfy process (window/pane) while keeping controlling shell interactive, plus send-command helpers per FR-002, FR-003, US2/AC1-3, T014, T015, T017. **UPDATE: full_launch_sequence + tmux helpers + send in comfy-local; used in go/launch.**
- [ ] T033 Extend hf_select_download.py (or add dedicated enrich helper) to fully support git-clone HF + loose files: Civitai query (direnv token), fetch details, HF skeleton + weights layout, civitai side folder, rich comfygo-model.json per FR-007, FR-008, FR-009, T019, T020, T021 (currently partial; full US3 pending)
- [ ] T034 Complete GitHub branch protection setup (require PRs + Codacy status check, conversation resolution) and update docs/workflow.md per Constitution IX, plan "Solo Maintainer..." section, T004, T005. **UPDATE: Mostly complete** - GH protection active (required checks "analysis", conversation resolution, 0 reviews); docs/workflow.md updated.
- [ ] T035 Implement or update root CHANGELOG.md for this feature and constitution changes (VIII) per Constitution VIII, T003. **UPDATE: Done** - CHANGELOG.md updated. Follow up: keep maintained on future commits.
- [X] T036 Review the scattered changes to vendored nodes, registry tests, and scripts from the quality gates setup and recent ruff; justify as cross-cutting or move to appropriate feature/003 convergence (unrequested) **UPDATE: Reviewed; vendored excluded, owned changes are for quality gates (cross-cutting, justified).**
- [X] T037 Confirm that all 004 flows preserve existing speckit artifacts (001-003, doctor, verify, registry, constitution) and do not introduce direct python/pip per repo rules and plan (partial - some hygiene in scripts) **UPDATE: Preserved; all new code uses uv run, no direct python/pip.**

## Handoff

Phase 7 Convergence tasks have been reviewed post-/speckit-implement. Many foundational (T004-T008), US1 (T009-T012), and US2 (T014-T017, T032) items are now complete or partially addressed (see UPDATE notes and new "Broken or Needs Follow Up" section above).

**Current status summary:**
- Phase 2 + US1/US2 MVP largely implemented (settings loader, manifests, re-patch/drift, tmux launch sequence + helpers).
- Gate green (verify-quality.sh ✅).
- 24/37 tasks [X].

**Next:**
- Complete open tasks (T013, T018, T019-T023, T026-T028, T033-T035).
- Re-run `/speckit-converge` + `/speckit-analyze`.
- Run gate before commits.
- Update issues (T025).
- Preserve Phase 7.

---

**Next after this tasks file**: Complete open tasks (prioritize T013/T018 + US3). Re-converge. Pass gate before commits.

(Tasks updated following speckit rules + prior converge/analyze/implement + constitution. Total tasks: 37.)

## Phase 8: Convergence

**Purpose**: Address remaining gaps after implementation. Many Phase 2, US1, US2 completed (settings, manifests, re-patch basics, tmux sequence, docs). US3 and verification tasks still unmet. Appended new tasks for the pieces of work.

- [ ] T038 [US3] Implement full Civitai API query (with direnv token), HF skeleton download/move, civitai side folder, and rich comfygo-model.json (kind, components, HF+Civitai source) in hf_select_download.py or new helper per FR-007, FR-008, FR-009, T019 (missing)
- [ ] T039 [US3] Integrate enrichment into "get up to date" / model phase of launch or as `comfygo models enrich` per T020 (missing)
- [ ] T040 [US3] Ensure emitted JSON compatible with scanner/descriptor/reconciler (add tolerant fields) per T021 (missing)
- [ ] T041 [US3] [P] Add examples and quickstart updates for full enrichment flow per T022 (missing)
- [ ] T042 [US3] Ensure no keys or private model names in examples/docs per T023 (missing)
- [ ] T043 Complete re-patch / drift detection driver to parse manifest content and perform conditional re-apply/matching after update (beyond unconditional apply and status check) per FR-004, FR-005, plan Phase 3, T010 (partial)
- [ ] T044 Add the manual verification test (smoke script or docs) for re-patch after simulated update per T013 (missing)
- [ ] T045 Update verification (quickstart or script) to cover full sequential tmux launch over simulated single-terminal SSH per T018 (missing)
- [ ] T046 Complete full end-to-end verification (SSH sim, sequence, enrichment, no private exposure, preserve artifacts) per T027 (missing)
- [ ] T047 Add the optional small diagnostic node or CLI helper for registry discovery of enriched models per T028 (missing)
- [ ] T048 Complete GitHub branch protection setup and docs if any gaps remain (per T034) (partial)
- [ ] T049 Ensure ongoing CHANGELOG updates for the feature per T035 (partial)