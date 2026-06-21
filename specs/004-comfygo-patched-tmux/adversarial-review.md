# Adversarial Review: Comfygo Patched Tmux Control (004) - Post-Implementation + 005 Consolidation

**Feature**: specs/004-comfygo-patched-tmux  
**Review Date**: 2026-06-22 (post-005-single-entrypoint implementation for docs/constitution, post Phase 12/13 append in 004/tasks.md, post consolidation cleanup to make 004 the master tracking feature)

**Previous context**: Original adversarial review (2026-06-21) identified stale claims, vague language, missing precision in manifests/JSON/contracts, contradictions on optionality. Led to clarifications, spec/plan/tasks updates, Phase 10/11 impl claims for US3/enrich/re-patch, Phase 11 cleanups. 005 was then executed separately for single-entrypoint docs/constitution enforcement (per user request and constitution alignment). Recent work: 005 impl completed (README/workflow/model-library updated to lead with `comfygo`, constitution reinforced under III with "single entry point principle", version to 1.2.1, CHANGELOG, gates passed); 004 Phase 12/13 now tracks remaining with T072/T073 [X] cross-referenced to 005; feature.json and AGENTS marker point to 004 as consolidated master.

**Scope of this review**: Read-only adversarial review focused on **all implementation** (code + docs + governance) done so far across 004 (Phase 10/11 "completed" claims + internal changes) and 005 (docs/constitution), plus current state of pending items in Phase 12/13, before attempting to finish the remaining code items (T079+ for doctor/enrich/re-patch driver). Inspects actual files vs spec/plan/tasks intent, constitution, safety (single entrypoint, no silent failures, no secrets, preserve artifacts, uv-first, verifiable). Does **not** review historical superseded phases in detail unless they affect current claims. Uses file-by-file pattern for implementation code/docs.

**Artifacts reviewed**: spec.md, plan.md, tasks.md (esp. Phase 10-13), 005 spec/plan/tasks (for cross-consolidation), README.md, docs/workflow.md, docs/model-library.md, .specify/memory/constitution.md, CHANGELOG.md, scripts/comfy-local, scripts/hf_select_download.py, scripts/comfygo, comfyui-patches/manifest.md, comfy-cli-patches/manifest.md, scripts/comfygo-verify, scripts/test-repatch-smoke.sh, custom_nodes/comfygo_model_registry/ (limited to interface), verify-quality.sh calls.

**Review type**: Primarily code-level + docs/governance implementation review (file-by-file), with alignment check against design artifacts. Feeds into /speckit-clarify if needed before final impl of remaining.

## Executive Summary

**Feature direction assessment**: Core vision remains strong and constitution-aligned: reliable vendored patching + re-patch resilience via manifests, one-command `comfygo` launch (update/verify/tmux for SSH single-terminal), preferred HF git-clone + Civitai enrichment producing rich `comfygo-model.json` + side folders usable by registry. 005 work successfully enforced the "single memorable entry point" UX in all user-facing docs and constitution (good). Phase 10/11 landed substantial code (enrichment exposure, basic re-patch conditional, tmux, settings, doctor extensions, smoke script, gates, protection).

**Is it safe to proceed to finish remaining items?** **No, not without remediation of current implementation gaps vs claims.** The "implemented" parts have several places where code/docs do not match the "completed" assertions in tasks/plan (e.g. enrichment "integrated" but launch is still stub; re-patch "structured" but code is simple grep; doctor extensions but full GCD 16-scenario guided experience remains in separate verify script, not under main `comfygo doctor`). Single entrypoint is now prominent in docs/constitution but not fully realized in code (doctor/enrich/launch still have split or stub behavior). Stale/outdated text in tasks.md (even post-cleanup) and safety-critical underspecification in contracts remain risks for finishing T079+ (could re-introduce silent failures, data issues, or contradict FR-004/005/013, Error and Exit Contracts, 003 doctor extend, 005 single-entry).

**Biggest remaining problems (ranked by severity)**:
- **CRITICAL/HIGH (safety + single entrypoint violation + credibility)**: Enrichment integration in launch (T070/T058) is still a no-op stub (`--help > /dev/null`) despite "implemented" claims and "integrated" language in tasks. Re-patch driver (T071/T059) uses simple grep/parse despite "structured per manifest" comments and claims of following Error and Exit Contracts. `comfygo doctor` (T069) does useful checks (protection, drift, registry reconcile dry-run) but lacks full 16 GCD scenarios, action inventory, recommended-next, --apply blocking (those live only in `comfygo-verify`). This directly contradicts 003 plan/FRs, 004 FR-013 (preserve + single entry), 005 spec (one command for doctor/enrich), and Phase 12/13 intent. Users cannot reliably use the "single `comfygo`" for the guided doctor experience or auto-enrich during launch.
- **HIGH (silent or incomplete behavior + contract violations)**: Re-apply and drift logic swallows errors (`|| true` on apply scripts), uses output-grepping instead of structured manifest parsing (Patched Files/Historical Names/Rationale sections exist in manifests but under-used). Launch sequence calls full `verify-quality.sh` (lint/tests) mid-sequence — risk of aborting user launch on hygiene issues or performance. No explicit dry-run for full sequence re-patch/enrich.
- **MEDIUM (alignment + maintenance risk)**: Docs/constitution now good for 005 (single entrypoint highlighted, internals de-emphasized to bootstrap notes), but code still has direct internal script calls (fine) and outdated comments claiming "enhanced/structured" where partial. Phase 12/13 text cleaned in this session but historical "Phase 10 completed" claims in top handoff and superseded sections still pollute (makes it hard to know current state). 005 tasks/plan were narrow (docs only), but cross-consolidation into 004 is good; T075 now [X] but low items (T076/T077 audit/clean) pending.
- **MEDIUM/LOW**: Privacy/secret safety good in principle (redaction in py, high-level only in docs) but verify during launch could log sensitive if not careful. No data-model/contracts for 004 (unlike 002/003), relying on prose + Phase 12. Some "rich" language remains in spec (intentional per prior review but needs exact schema refs in code paths).

**Recommendation**: Feed this review into `/speckit-clarify` (reference this doc) to update 004 spec/plan/tasks (fix stale claims, add exact contracts for remaining, operationalize single entrypoint in code paths). Fix the implementation gaps in "done" parts (un-stub enrich in launch, enhance driver to structured, surface full GCD in `comfygo doctor` or unify with verify) *before* or as part of finishing Phase 13 items. Re-run text audit, converge, gate. Only then implement T079+ with the safety matrix. Do not claim "single entrypoint complete" until doctor/enrich/launch/re-patch are all under `comfygo` without stubs/splits. The 005 docs work is solid; code must catch up to match the UX promise.

## Safety Principles

Non-negotiable. Must hold in all code, docs, manifests, constitution, tasks, and future changes. Violations are CRITICAL.

### Single Entry Point Must Be Complete and Functional (not just documented)
**FORBIDDEN**:
- Leaving core daily ops (doctor with full GCD, auto-enrich during launch, re-patch) in separate scripts/verify or as stubs while docs/constitution promise "one command `comfygo`".
- `comfygo doctor` or launch claiming full guided/ integrated behavior when GCD/enrich/re-patch logic is incomplete or split.

**REQUIRED**:
- `comfygo doctor` must surface full 16 GCD, inventory, recommended action, --apply (unify or delegate from verify under the entry point).
- Launch sequence must actually perform enrichment (call the logic, not stub) when `COMFYGO_ENRICH_CIVITAI=1`.
- Re-patch/drift must use the manifest structure for conditional logic + exact Error and Exit Contract messages.
- All user-facing flows must be reachable via `comfygo` / subcommands; internals only for bootstrap/debug (as per 005 docs).

### Re-Patch / Drift / Enrichment Must Be Non-Destructive, Explicit, and Contract-Driven
**FORBIDDEN**:
- Silent failures, swallowed errors (`|| true` without logging exact contract message), unconditional applies that could corrupt running ComfyUI or user data.
- Writing descriptors with tokens/secrets or on failure without graceful basic usable output.
- Using non-structured (simple grep) matching when manifests provide Historical Names / Rationale sections.

**REQUIRED**:
- On mismatch: exact historical name/path from manifest + current file + "edit ... in this repo and re-apply" (per FR-005, Error Contracts).
- Enrichment: on Civitai/HF failure (no token etc.) produce basic usable `comfygo-model.json` from local only (per FR-008, Key Entities example with source.hf + civitai|null); always redact; side folder atomic.
- Driver must parse manifest sections; conditional re-apply only; dry-run/status/doctor must surface without mutation.
- During tmux: do not disrupt running ComfyUI unless explicitly requested.

### Launch/Doctor/Verify Must Be Strictly Ordered, Verifiable, SSH-Safe, and Not Harmful
**FORBIDDEN**:
- Reordering steps (settings before mutation; patch -> verify -> tmux).
- Running full quality/lint gate (`verify-quality.sh`) as part of every user launch (can abort or slow; hygiene is pre-commit, not runtime).
- GUI/X11 assumptions; must work with direnv only.

**REQUIRED**:
- `full_launch_sequence` strict: update/patch (with re-patch driver) -> (enrich if enabled) -> verify (feature state, not full lint) -> tmux (or fallback).
- Every run produces sequential logs/doctor output to verify sequence.
- Doctor provides actionable inventory + recommended + blocking apply for safety scenarios (GCD).
- All changes pass local gate (`./scripts/verify-quality.sh`) before commit; uv-first only; preserve 001-003 artifacts + FR-013.
- Constitution III (Safe Daily + single entry), V (no secrets), VI (uv), VII (verifiable), IX (gate + protection) are gates.

### Documentation and Governance Must Match Reality (Single Entry + No Stale Claims)
**FORBIDDEN**:
- Docs/constitution promising "one `comfygo`" for doctor/enrich while code has stubs/splits.
- Stale "Phase 10 completed" or "implemented" claims in tasks/plan when gaps remain (maintenance/safety hazard for future changes).

**REQUIRED**:
- All primary user examples lead with `comfygo` (or sub); internals only in explicit bootstrap/contributor notes (as done in 005 updates).
- Tasks/plan must accurately reflect current state (use Phase 12/13 for pending; update handoff after fixes).
- Constitution reinforcement (single entry) must be reflected in code behavior, not just text.
- CHANGELOG updated for all user-facing + significant changes.

## Artifact Alignment Check

**spec.md / plan.md / tasks.md (004 + 005 cross)**:
- Good: 005 docs/constitution now match FR-003/FR-004/SC-002/003 (we updated them; single entrypoint callouts, `comfygo models enrich`, bootstrap notes, constitution text + v1.2.1).
- Problems: Phase 10/11 handoff and top "Next" still have outdated "completed" language (even post-cleanup in this session); tasks claim "enrichment integrated" / "re-patch ... structured" / "doctor extensions" but code inspection shows stubs/partial/simple grep/limited doctor. Plan Phase 4 says "extend hf helper" and "integrated", but launch has stub. No explicit contracts/README or data-model for 004 (relies on prose + Phase 12; risks divergence). Spec FR-008/009/Edge Cases precise on graceful + usable JSON, but current "implemented" code paths don't fully honor in launch. T075 now [X] good, but low items (T076/T077) and T074 still pending. 005 spec/plan correctly narrow (docs only); consolidation into 004 Phase 12/13 is correct per T075 intent.
- Stale in 004 plan: references to old dates/claims; "Next" sections historical but polluting.

**005 artifacts vs 004 cross**:
- 005 spec/plan/tasks were executed correctly for their scope (no code changes; focused on docs/constitution/single entry). Updates to README/workflow/model-library/constitution/CHANGELOG/ quickstart checklist align with 005 FRs, research decisions (scope, renames to comfygo models enrich, bootstrap notes), contracts (Primary Command Surface + allowed bypasses). Good. No contradictions introduced.

**Code vs design (implementation gaps)**:
- See file-by-file below. Claims in tasks (Phase 10 "enrichment integrated", "re-patch ... with exact messages", doctor in single entry) do not match runtime behavior.

**Constitution alignment**:
- Strong on paper (I vendored, II explicit refresh, III safe daily + single entry now reinforced, V secret, VI uv-first in calls, VII verifiable via doctor/logs, VIII changelog updated, IX gate + protection).
- In practice: uv-first good (calls use `uv run --no-project`); no secrets in committed (manifests high-level, py redacts); gate runs before our changes (green); but runtime verify call in launch and partial driver/enrich/doctor risk violating "verifiable" and "safe daily" if users hit stubs or splits. Preserve FR-013: existing registry/doctor/verify artifacts still present and functional (yes).

**Other**: No data-model/contracts for 004 (gap noted in prior review; Phase 12 uses prose). Manifests are structured (good, sections present). 005 quickstart/contracts/data-model updated where relevant for its scope.

## File-by-File Review

### `scripts/comfy-local`

**Current role**
Main bash script implementing settings loader (COMFYGO_* from .comfygo-settings or env), full_launch_sequence (patching via install-to-comfyui, conditional re-patch via drift, enrichment stub, verify-quality call, tmux_launch), doctor (protection, paths, patch/drift, registry reconcile dry-run snapshots, runtime env, model root checks), models dispatch (if "enrich" then call hf py with uv; else registry cli), patch_drift_check (manifest grep for .patch + state), tmux helpers, various require_* and reconcile helpers. Called by scripts/comfygo thin wrapper. Also handles status, sync, patch-*, refresh-upstreams, etc. by delegating to other scripts.

**Issues / risks**
- Lines 1073-1078 (enrichment in full_launch_sequence): if [[ "${COMFYGO_ENRICH_CIVITAI:-0}" == "1" ]]; then echo "..."; uv run ... hf_select_download.py --help > /dev/null 2>&1 || true; # for full, user can run `comfygo models enrich` ... fi . This is a no-op stub. Contradicts Phase 10 "enrichment integrated", T058 "integrate ... or expose", T070 "actually call the enrich logic", plan Phase 4, FR-002/008, 005 single-entrypoint (launch should do it). Auto-enrich during "get up to date" does not happen.
- Lines 1057-1071 (re-patch in launch): for pdir ... patch_drift_check ... ; if ... | grep -q "not applied"; then ... apply-*.sh || true . Calls the (simple) drift check twice in some paths; uses output grep instead of parsing manifest sections (Patched Files/Historical Names/Rationale are in manifests but code treats as simple list). || true swallows errors. Comments claim "enhanced driver (T059): conditional based on drift, structured per manifest, per Error and Exit Contracts" but impl is partial/simple. Risks silent or incorrect re-apply (violates FR-004/005, Error Contracts, T071).
- doctor() ~834+: Extensive checks (protection via gh, uv, COMFYUI_DIR, patch_state + drift, runtime env, llama, registry source/runtime copy, model_root, reconcile dry-run with before/after snapshot via comfygo-models.sh, views diff). Good coverage for many scenarios. However, no full 16 GCD scenarios (GCD-001..016 from 002/003), no action inventory, no "recommended next action", no --apply support that blocks until "PASS: all 16". The GCD harness and safety scenarios live in scripts/comfygo-verify (separate). Contradicts T069, 003 T063-T066 (extend doctor in single entry), 004 FR-013 (preserve + single entry), 005 spec (one command for doctor), Phase 12/13. `comfygo doctor` is not the "guided" experience.
- Line 1081: "$repo_dir/scripts/verify-quality.sh" || { echo "Verify failed, aborting launch"; exit 1; } . Runs full gate (ruff, shellcheck, bandit, registry tests, hygiene) as part of *every* launch sequence (after enrichment, before tmux). Risk: aborts user launch on lint/dirty tree issues; performance cost; hygiene is pre-commit per AGENTS/constitution IX, not runtime verification of feature state. Not aligned with "verification steps" intent in spec (should be feature state like paths/patches/registry, not full quality).
- Direct delegation to internal scripts (install-to-comfyui.sh, apply-*.sh, comfygo-models.sh, verify-quality) inside the "single `comfygo`" path. Fine for internal (docs now correctly de-emphasize for users), but the 005 single-entrypoint promise requires that *user* experience is through `comfygo`; code comments and partial impl undermine "one command" for advanced flows.
- models) dispatch ~1150: if enrich then uv python hf... else run_model_registry_cli. Good for user `comfygo models enrich`. But launch doesn't use the dispatch for auto.
- Overall: many || true and set -euo pipefail interactions; error paths may not produce exact contract messages. Single entrypoint wrapper (comfygo) is thin and good, but sub-behaviors (doctor/enrich/launch re-patch) not unified.

**Needs to handle/change**
- Replace enrichment stub (1074-1078) with actual call: determine model root, call the enrich logic (respect COMFYGO_ENRICH_CIVITAI, direnv tokens, produce descriptor/side folder) or delegate to `comfygo models enrich` equivalent internally for auto case. Log what was done.
- Enhance patch_drift_check (155+) and call sites to parse manifest sections (use awk/sed or simple parser for ## Patched Files / ## Historical Names / ## Rationale); use Historical Names for matching; produce exact FR-005 message on mismatch; make conditional re-apply use the structured info.
- Unify/integrate full GCD from verify into doctor() (or make doctor the entry that runs the guided harness): output inventory of GCD-001..016, recommended action, support --apply <id> with prompts/ --yes, block mutating actions until PASS all 16. Update usage and status output.
- Remove or gate the verify-quality.sh call in launch (1081); make it doctor-only or settings-controlled (e.g. COMFYGO_VERIFY_ON_LAUNCH=0). Verification in launch should be feature-state (paths, patches, registry, drift), not full lint gate.
- Update all comments claiming "structured/enhanced/integrated/completed" to match reality or fix code to match (e.g. line 1057 comment).
- Ensure error paths and mismatch messages exactly match Error and Exit Contracts (historical name + current file + "edit in repo and re-apply").
- For single entrypoint: ensure `comfygo` (and sub) are the only promoted user surface; internal delegations are implementation detail.

### `scripts/hf_select_download.py`

**Current role**
Python CLI (argparse) for HF git-clone / loose file download + optional Civitai enrichment. Supports package mode (canonical layout), resume, --only-missing, category mapping, descriptor write (comfygo-model.json with source.hf + civitai), civitai side folder (info.json), metadata. Redacts tokens. Builds rich descriptor with kind/components. Called via `uv run --no-project` from comfy-local (for enrich) or direct hf-select-download wrapper. Produces output usable by registry (per FR-009).

**Issues / risks**
- Good: civitai fetch (_fetch_civitai), side folder, descriptor with source (hf + civitai|null), graceful on no token (local info only), redaction, uv-first call site. Matches Key Entities example and FR-008 "basic usable on failure".
- No major in core logic from spot checks (end of file shows package root + "next: comfygo models reconcile --apply").
- Risk: when called from launch stub, it does --help only (no actual work). When called by user `comfygo models enrich`, it does full work. Inconsistent behavior depending on path.
- If COMFYGO_ENRICH_CIVITAI=1 but no tokens in env, still runs but should be no-op or basic (code handles via _read_token etc.).
- No explicit handling for the "auto in launch" case (the stub bypasses the full path).
- Write descriptor always? Flags control (write-descriptor, overwrite). Good, but launch stub never reaches here.

**Needs to handle/change**
- No changes needed to the enrichment logic itself (it is complete and safe per prior review + 005 Key Entities).
- Ensure it is *actually called* with real args (model root or source) from launch when enabled (fix in comfy-local).
- Add/ensure logging when called from auto-launch path (e.g. "auto-enriching $model_root because COMFYGO_ENRICH_CIVITAI=1").
- Verify in tests/smoke that descriptor has exact schema with source.hf + civitai (as in 005 data-model/contracts).
- If called without tokens and COMFYGO_ENRICH=1, produce minimal + log "Civitai skipped (no token or disabled)".

### `scripts/comfygo`

**Current role**
Thin bash wrapper: if no args, exec comfy-local "go"; else exec comfy-local "$@". Adds scripts/ to PATH via .envrc (direnv). Makes `comfygo` the single memorable entry point.

**Issues / risks**
- None major. Correct thin facade for single entrypoint (per 005 FR-001/002, constitution III).
- Good: delegates everything; supports subcommands including models enrich (via dispatch).
- Minor: `comfygo --help` shows usage from comfy-local (which we updated in T010 to list "models enrich <source>"); good.
- Risk: if direnv not active, falls back to .env.local (per code); docs now explain this for bootstrap.

**Needs to handle/change**
- No changes. Keep as the one command users remember. Update any remaining comments if they mention direct scripts for normal use.

### `README.md`, `docs/workflow.md`, `docs/model-library.md`

**Current role** (post-005 impl)
User-facing docs. Now updated per 005 tasks T006-T009, T013-T018: lead with `comfygo` (or sub like `comfygo models enrich`) for daily flows (launch, doctor, models, sync, refresh, patch); direct scripts only under explicit "bootstrap / advanced / contributor" headings with "prefer `comfygo`" redirects and notes. README has prominent "Remember one command: `comfygo`" callout + explanation. Workflow enrichment/patch sections updated. Model-library HF examples all use `comfygo models enrich` (with bootstrap note for direct); GC examples use `comfygo models gc` or note advanced raw form. Aligns with 005 contracts (Primary Command Surface + allowed bypass headings + Specific Renames) and research decisions.

**Issues / risks**
- Generally good and improved. All primary examples now start with `comfygo` or sub.
- Remaining direct script examples are correctly in bootstrap sections (e.g. README "Comfy CLI Wrappers (bootstrap / advanced)", workflow "Direct `scripts/hf-select-download` remains for bootstrap...", model-library prose "direct `scripts/hf-select-download` for bootstrap only").
- Minor inconsistency: README command map / callout good, but some older sections (e.g. "When a workflow says a model is missing") still reference `comfygo models` correctly; no bare scripts in top-level.
- Risk: if user follows bootstrap notes without reading the "prefer `comfygo`" text, they might remember scripts. But per contracts, this is allowed.
- 005 quickstart scenarios now pass (greps show no bare in primary; positive for `comfygo models enrich` in workflow/model-library; README has callout).
- Constitution cross-ref good.

**Needs to handle/change**
- No major. Optionally strengthen bootstrap notes with "after one-time setup, always use `comfygo ...` for muscle memory".
- Ensure any new examples (e.g. in future smoke docs) follow the rule.
- In model-library, the GC examples updated; the "next: comfygo models reconcile" in py output is user-facing good.
- Run the mechanical greps from 005 quickstart Scenario 5 as part of verification.

### `.specify/memory/constitution.md`

**Current role** (post-005)
Core principles I-IX. III Safe Daily Operation now includes the added "single entry point principle" paragraph (exact from 005 research draft): "all user-facing documentation... MUST present `comfygo` (and its subcommands such as `comfygo doctor`, `comfygo models enrich`, `comfygo sync`) as the one command... Direct paths... belong in "For contributors", "Quality gates", "Power users", or "Debugging" sections only." Version bumped to 1.2.1 (PATCH per Governance for clarifications); Last Amended 2026-06-22 + comment note referencing 005 and 004 Phase 12 T073. Aligns with 005 FR-004, clarifications, constitution Governance.

**Issues / risks**
- Good update. Reinforcement is under existing III (not new principle, correct per research).
- The text correctly de-emphasizes internals while allowing bootstrap/debug sections.
- No weakening of other principles (I vendored preserved, II explicit refresh, V secret, VI uv, VII verifiable, VIII changelog, IX protection/gate).
- Risk: the "MUST present `comfygo`" is now in constitution (binding); current code partially satisfies (wrapper is there, docs updated, but doctor/enrich/launch have internal stubs/splits). Must fix code to match or the constitution claim is aspirational only.
- Top sync impact report is historical (1.1->1.2.0); the version line + comment is sufficient.

**Needs to handle/change**
- No text change needed (005 update was correct).
- Code must be brought into alignment (see above files) so that "single entry point" is not just documented but functional (doctor/enrich/re-patch under `comfygo`).
- When finishing remaining, update the comment or add "005 docs + code unification" note if further amendment.

### `comfyui-patches/manifest.md`, `comfy-cli-patches/manifest.md`

**Current role**
Structured manifests with ## Patched Files, ## Historical Names, ## Rationale (and version/purpose). Used by drift check and re-patch logic. Public, non-secret (high-level names + rationale only). Good per FR-004/005, Key Entities, Error Contracts.

**Issues / risks**
- Good structure (sections present, as expected by Phase 12/13 and T071).
- Code (comfy-local) under-uses the structure (simple grep for .patch lines; doesn't parse Historical Names for matching or Rationale for messages).
- Manifests themselves clean (no secrets).

**Needs to handle/change**
- No change to manifests.
- Driver code must parse the sections (see comfy-local).

### `scripts/comfygo-verify`, `scripts/test-repatch-smoke.sh`

**Current role**
comfygo-verify: the full harness with GCD 16 scenarios (dry-run, apply, safety, evidence, etc.), used for CI/live validation, separate from main doctor. test-repatch-smoke.sh: smoke for re-patch after simulated update + full sequence over SSH sim (per T060).

**Issues / risks**
- Good: these implement the missing pieces (GCD, smoke) referenced in Phase 12/13 and T069/T060/T061.
- Risk: they are not integrated into the main `comfygo doctor` / `comfygo` flows. Users running the "single entry point" doctor do not get the GCD experience or easy smoke. Contradicts single-entrypoint UX (005, FR-013, T069, T074).
- Smoke script exists and was added (good per T060).
- No major safety issues in the harnesses themselves (they are for validation, use temp roots, etc.).

**Needs to handle/change**
- Integrate: make `comfygo doctor` (or `comfygo doctor --full-gcd` / default) run or include the GCD scenarios from verify; output inventory + recommended + --apply support (T079/T074).
- Document `comfygo doctor --smoke-repatch` or equivalent that invokes the smoke under the entry point.
- Keep the separate scripts for CI/ advanced (per 005 bootstrap notes), but surface under `comfygo`.

### `README.md` / docs / constitution (cross-check with code)

**Current role** (post-005)
As above: now correctly promote single `comfygo`. Bootstrap sections have direct scripts with clear "prefer `comfygo`" notes. Good alignment with 005 contracts/research.

**Issues / risks**
- See file sections above. The docs are ahead of the code in some places (promise full single entry for doctor/enrich/launch, but code has stubs/splits).
- No promotion of internals in top-level (good).
- Constitution text is binding; code must deliver.

**Needs to handle/change**
- No doc changes (005 work was correct and complete for its scope).
- Code changes (as above) to make the documented behavior real.
- After code fixes, re-run 005 quickstart scenarios + mechanical greps to confirm still pass.

### Other (CHANGELOG.md, verify-quality.sh, registry __init__.py, etc.)

**Current role**
CHANGELOG has 005 entry (good, per VIII). verify-quality.sh: the gate (ruff on owned, tests, etc.; called in launch and pre-commit). Registry: the scanner/reconciler/descriptor for `comfygo-model.json` (used by doctor dry-run, reconcile, nodes).

**Issues / risks**
- CHANGELOG good.
- Gate is correct for pre-commit; its call in launch is the risk (see comfy-local).
- Registry still functional (preserve FR-013); dry-run snapshots in doctor good.
- Minor: some registry tests or harnesses may assume direct scripts; update if needed for single entry (low).

**Needs to handle/change**
- Remove/gate the gate call from launch sequence.
- Ensure all preserve tests still pass after doctor/enrich/re-patch unification (T079+ must run existing harnesses).

## Summary Table (Severity-Graded Findings on Implementation)

| # | File | Issue | Severity | Recommendation |
|---|------|-------|----------|----------------|
| 1 | scripts/comfy-local (launch) | Enrichment stub (lines 1073-1078): --help > /dev/null instead of actual call when COMFYGO_ENRICH_CIVITAI=1 | HIGH | Replace stub with real enrich call (use model root, delegate to logic or `comfygo models enrich` equivalent); log action |
| 2 | scripts/comfy-local (re-patch + drift) | Simple grep + output-grep instead of structured manifest parse (lines 155+, 1061-1063); comments claim "structured" | HIGH | Parse ## Patched Files / Historical Names / Rationale sections; use for matching + exact FR-005 messages; remove output grep |
| 3 | scripts/comfy-local (doctor) | Limited doctor() (~834+); full 16 GCD / inventory / recommended / --apply only in separate verify script | HIGH | Integrate/unify GCD harness into `comfygo doctor` (inventory output, recommended action, --apply support, block until PASS all 16); keep verify for CI |
| 4 | scripts/comfy-local (launch) | verify-quality.sh call mid-sequence (line 1081) aborts launch on hygiene | MEDIUM | Remove or make COMFYGO_VERIFY_ON_LAUNCH=0 (default off); launch verification should be feature-state only |
| 5 | scripts/comfy-local (general) | || true on apply/re-patch swallows errors; no exact contract messages | HIGH | Propagate or catch to emit exact "historical name + current + edit in repo" per Error Contracts |
| 6 | scripts/comfy-local + hf py | Launch stub bypasses full enrich path (inconsistent with user `comfygo models enrich`) | MEDIUM | Make auto case call the same logic; add "auto-enrich because COMFYGO_ENRICH=1" log |
| 7 | All (comfy-local, docs, tasks) | "Implemented" / "integrated" / "structured" claims in Phase 10/11/plan vs partial reality | MEDIUM | Update tasks/plan/handoff comments to accurate state; only claim after fixes |
| 8 | docs (post-005) + code | Single entrypoint prominent in docs/constitution but not fully in doctor/enrich/launch behavior | HIGH | Code fixes (1-3) required to match 005 FR-001/003/004 and constitution reinforcement |
| 9 | manifests + code | Manifests structured (good); code under-uses sections | LOW | Driver must parse sections (see 2) |
| 10 | scripts/comfygo-verify + comfy-local | GCD/smoke exist but not surfaced under main `comfygo doctor` | MEDIUM | Integrate per 3 and T074/T079; document `comfygo doctor --smoke-repatch` |

## Remediation Order (Before Finishing Remaining Phase 13 Items)

1. **CRITICAL (un-stub + unify)**: Fix enrichment in launch (T080/T070) + integrate full GCD into `comfygo doctor` (T079/T069) + enhance driver to structured (T081/T071). These are the core "single entrypoint" gaps.
2. **HIGH (safety contracts)**: Fix error handling / exact messages in re-patch paths; ensure graceful descriptors on failure.
3. **MEDIUM (alignment)**: Remove gate call from launch; update all stale "completed" claims in tasks/plan/handoff (T078 etc.); run text audit + converge post-fixes.
4. **LOW**: Polish notes, ensure smoke under entry point (T082), final handoff (T084), audit (T083).
5. Only after 1-3: implement remaining Phase 13 tasks with the Safety Test Matrix below. Re-run 005 quickstart scenarios + greps + full gate.

## Safety Test Matrix (for remaining + current gaps)

**Dry-run / no-mutation**:
- `comfygo doctor` (and with COMFYGO_ENRICH_CIVITAI=1): must run full GCD 001-016 dry-runs, produce inventory + recommended, no trash/views change on live root.
- Launch with settings but no --apply: must do patch/drift/enrich checks (actual enrich if enabled), verify, but no tmux launch if dry.

**Apply gates**:
- `comfygo doctor --apply <gcd-id>` or recommended: only after all 16 PASS; prompts unless --yes; non-interactive --yes only if ready.
- Re-patch after simulated `comfy update` (use smoke script or manual): must detect via manifest, emit *exact* historical + current + "edit in repo" message, then re-apply only on user action.

**Quarantine / symlink / safety (GCD scenarios)**:
- All 16 from 002/003 doctor-matrix must pass under `comfygo doctor` (temp roots + live if --models-dir).
- Symlinked managed folders: refuse; no .comfygo_trash on live; source unchanged on dry-run.

**Enrichment end-to-end (with/without token)**:
- `comfygo models enrich <hf-clone>` or loose: produces HF layout + civitai/ + comfygo-model.json with source.hf + civitai (or null); registry reconcile works; node can discover by kind.
- No token or COMFYGO_ENRICH=0: still produces basic usable descriptor (local info only); no secrets written; side folder only if civitai match.
- During launch (COMFYGO_ENRICH=1): actual enrichment happens (not stub); logged.

**Re-patch / drift / manifest**:
- Mismatch (historical name changed): exact message per contract; no silent apply.
- Manifest sections used for matching (Historical Names).
- During active tmux: re-patch does not kill running ComfyUI unless requested.

**Single entrypoint + SSH**:
- All flows (including doctor with GCD, launch with enrich, re-patch) via `comfygo` only (no bare scripts in user examples).
- Over plain SSH + direnv: works; no X11.
- `comfygo --help` surfaces enrich, doctor (full), etc.

**Integration / preserve**:
- Existing registry tests, 001/002/003 harnesses, verify-quality still green after changes (FR-013).
- Constitution: uv-first calls, no secrets in committed, gate before commit, protection active.

**Performance / edge**:
- Launch sequence strict order; logs sequential and verifiable.
- tmux not present: clear message + fallback documented.

## Verification Commands

```bash
# Text audit (vague patterns; exclude this review)
rg -n "simple|heuristic|as appropriate|reuse pattern|rich descriptors|graceful|practical|verification steps|clear, actionable message" specs/004-comfygo-patched-tmux/ --glob='!adversarial-review.md' || echo "No bad patterns (or only in intentional spec statements)"

# 005 quickstart scenarios (post-code fixes)
# Scenario 5 mechanical + positive
grep -n 'scripts/hf-select-download\|./scripts/update-from-upstreams.sh\|./scripts/install-to-comfyui.sh' README.md docs/workflow.md docs/model-library.md || echo "No bare in primary (good)"
grep -l 'comfygo models enrich' README.md docs/workflow.md docs/model-library.md || echo "Missing in some"

# Code smoke (T060/T079+)
./scripts/test-repatch-smoke.sh
UV_CACHE_DIR=/tmp/uv-cache ./scripts/comfygo-verify --fast || true

# Doctor / GCD under single entry (after T079)
./scripts/comfygo doctor
./scripts/comfygo doctor --help  # should surface full GCD / --apply

# Launch with enrich (after T080; use temp or real with COMFYGO_ENRICH_CIVITAI=1 + tokens in direnv)
COMFYGO_ENRICH_CIVITAI=1 ./scripts/comfygo  # check logs for actual enrich, not stub

# Re-patch driver structured (after T081)
# Simulate update, run sequence, check exact message on mismatch

# Full gate (always before commit)
./scripts/verify-quality.sh

# Constitution / single entry grep
grep -A10 "single entry point principle" .specify/memory/constitution.md
grep -E '^comfygo ' README.md docs/workflow.md docs/model-library.md | head -5  # primary examples

# Registry / descriptor (enrich output)
comfygo models -f <enriched-name>
```

## What Not To Do

- Do not claim "enrichment integrated in launch" or "re-patch structured per manifest" or "doctor extensions complete" while the stub/grep/limited code remains (update claims only after fixes).
- Do not leave `comfygo doctor` or launch with behavior that contradicts the single entrypoint principle now in constitution and 005 spec/FRs.
- Do not run full verify-quality.sh as part of user launch sequences (hygiene is pre-commit gate).
- Do not use simple grep for drift when manifests have structured sections (parse them).
- Do not swallow errors in re-patch paths; must emit exact contract messages.
- Do not add new code changes without local `./scripts/verify-quality.sh` + pre-commit + (for PRs) status checks.
- Do not remove or change behavior of existing `comfygo_model_registry`, verify, GC harnesses, `.comfygo_views` (FR-013).
- Do not write descriptors with tokens or on failure without basic usable local fallback.
- Do not treat Phase 10/11 "completed" handoff language as current truth (use Phase 12/13 for pending).
- Do not implement T079+ until this review's findings are clarified/integrated and the Safety Test Matrix cases pass.

## Implementation Guidance (for T079+ / Phase 13)

Recommended order: fix the 3 HIGH in current "impl" first (enrich un-stub, driver structured, doctor unification), then the low cleanups. This makes the single entrypoint real before claiming done.

For enrichment in launch (T080):
- In full_launch_sequence, after re-patch block:
  if [[ "${COMFYGO_ENRICH_CIVITAI:-0}" == "1" ]]; then
    echo "=== Model enrichment (Civitai/HF) ==="
    model_root=$(models_root)
    if [[ -d "$model_root" ]]; then
      uv run --no-project python3 "$repo_dir/scripts/hf_select_download.py" --models-root "$model_root" --package-name "auto-enrich-$(basename "$model_root")" --write-descriptor --write-metadata || echo "Enrich skipped or partial (see above for graceful)"
    fi
  fi
- (Or delegate to a common enrich function that the models dispatch also uses.)

For re-patch driver (T081):
- Enhance patch_drift_check to:
  - Parse manifest for sections (e.g. awk '/## Historical Names/{flag=1;next} /##/{flag=0} flag && /-/ {print $0}' or simple state machine).
  - Use Historical Names list for matching (not just current .patch filename).
  - On mismatch: echo "historical name: $hist; current file: $current; edit $pdir/manifest.md and the corresponding .patch in this repo, then re-apply"
- In launch/doctor: use the structured result for conditional.

For guided doctor + GCD (T079):
- In doctor(): after current checks, source or exec the GCD scenarios from verify (or inline the 16 if small).
- Collect pass/fail per GCD-xxx.
- Print "Comfygo readiness / GCD inventory:" with available/blocked/not-relevant.
- Print exactly one "Recommended next action: ..." with rationale.
- Support `comfygo doctor --apply <action-id>` (reuse existing apply dispatcher from 003 work).
- Block mutating actions (sync, patch, enrich apply, reconcile --apply, launch if dependent) until "PASS: all 16 GCD scenarios".
- Update usage() and status to document the new output.
- Keep `comfygo-verify` for CI (it can call the same logic).

For launch sequence (general):
- Settings load first (already).
- Patch + re-patch driver (enhanced).
- Enrich (actual, if enabled).
- Feature verify (paths, patches, registry, drift, GCD dry if applicable) — *not* full quality gate.
- tmux_launch (or direct).
- Produce logs that allow verifying the sequence (echo "=== Step X: ..." ).

For single entrypoint consistency:
- `comfygo` (and subs) remain the only user surface.
- Update any remaining internal comments/docs that contradict (e.g. "use scripts/..." for normal flows).
- In doctor/launch output, mention "via `comfygo doctor` / `comfygo`" where helpful.

For T074/T082 (smoke integration):
- Add to doctor usage/output: `comfygo doctor --smoke-repatch` (or auto in recommended if drift).
- It should invoke the smoke harness (temp root, simulated update, check exact message + re-apply) under the entry point, with --keep-evidence support.

After changes:
- All existing tests/harnesses (registry, smoke, verify, 001-003) must still pass (run via gate).
- 005 quickstart scenarios + greps must still pass (docs unchanged).
- Constitution text remains accurate (code now matches the principle).
- Run the verification commands above + full gate.

## Definition of Done (Verifiable Checklist)

Before the feature (incl. remaining Phase 13 items) is considered complete:
- [ ] All Phase 13 tasks (T079-T084) marked [X] in tasks.md with accurate UPDATE notes.
- [ ] Enrichment actually happens in launch when COMFYGO_ENRICH_CIVITAI=1 (no stub; logs show real work or graceful skip).
- [ ] Re-patch/drift uses structured manifest parsing + produces exact Error and Exit Contract messages on mismatch; conditional and safe.
- [ ] `comfygo doctor` (the single entry point) surfaces full GCD 001-016 inventory, recommended action, --apply support; blocks mutating actions until PASS all 16; unifies with existing verify harness where possible.
- [ ] Launch sequence is strict (settings -> patch/re-patch driver -> actual enrich if enabled -> feature verify (not full gate) -> tmux); logs allow verifying order.
- [ ] No full `verify-quality.sh` in user launch paths (or explicitly settings-gated off by default).
- [ ] All Safety Test Matrix cases pass (dry-run, apply gates, GCD/quarantine, enrichment with/without token, re-patch exact messages, single entrypoint via `comfygo` only, SSH/direnv only, preserve existing artifacts/tests).
- [ ] Text audit clean (no new vague patterns in live spec/plan/tasks/docs; "rich"/"graceful" only in intentional contracts or safety statements).
- [ ] 005 quickstart scenarios + mechanical greps + new-user sim still pass (or updated if needed).
- [ ] `./scripts/verify-quality.sh` green (including ruff on owned, registry tests 113+, hygiene).
- [ ] Constitution III single entrypoint principle is reflected in *behavior* (not just text): doctor/enrich/launch/re-patch fully functional under `comfygo`.
- [ ] CHANGELOG updated for the code unification + any doc tweaks (Keep a Changelog).
- [ ] Handoff (T078) and top "Next" updated to "004 + carried 003/005 complete post-Phase 12/13; single `comfygo` entrypoint fully realized (docs via 005 + code unification); recommend commit + real-world test".
- [ ] No contradictions between 004 spec/plan/tasks and 005 artifacts (cross-consolidated).
- [ ] Gate + pre-commit + (for PR) status checks passed before any commit of these changes.
- [ ] Existing 001-003 artifacts, registry, verify, smoke, doctor partials, .comfygo_views all still functional and green (FR-013).
- [ ] Manual SSH sim (or real): `comfygo` (with settings) does full sequence, `comfygo doctor` gives guided GCD, `comfygo models enrich` works, re-patch after update gives exact message.

**Text audit post-remediation** (run this and confirm only intentional hits):
```bash
rg -n "simple|heuristic|as appropriate|reuse pattern|rich descriptors|graceful no-token|practical|verification steps|clear, actionable message" specs/004-comfygo-patched-tmux/ --glob='!adversarial-review.md' || echo "Clean (or only in spec contracts)"
```

This review is read-only. All findings are to be integrated via `/speckit-clarify` (reference this document) into the live spec/plan/tasks before or alongside finishing the code for the remaining items. The 005 docs/constitution work is a solid step toward the single entrypoint goal; the code must now deliver on it.

**End of review.**