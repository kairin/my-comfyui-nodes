# Research: Single Entrypoint CLI

**Feature**: 005-single-entrypoint | **Date**: 2026-06-22

## Research Areas

- Inventory of current user-facing command examples that bypass the single `comfygo` entry point.
- Best practices for documenting a single memorable CLI entry point in a wrapper-script project (promote the facade, document internals without teaching them as primary).
- Scope boundaries: which "docs" count as user-facing vs. implementation records (README + docs/*.md user sections + constitution vs. specs/* historical + AGENTS + issue templates + verify scripts).
- How the existing `comfygo models enrich` dispatch relates to documented `scripts/hf-select-download` usage (to decide rename-or-alias in prose).
- Constitution amendment style: reinforcement vs. new numbered principle (given clarifications specify "under Safe Daily Operation or a new note").

## Findings & Decisions

### Decision: Documentation update scope
- **Primary surfaces to edit**: README.md (user flows, command map, sync/refresh examples), docs/workflow.md (daily use, enrichment, updating sections), docs/model-library.md (HF download examples).
- **Do not edit for this feature** (or edit only incidentally): specs/*/ (these are implementation specs/quickstarts/contracts that describe the actual harnesses and cross-reference tasks; changing them would pollute history and is out of scope for "a new user" cognitive load reduction), AGENTS.md (agent instructions explicitly call out verify-quality.sh and pre-commit per quality gates), .github/ISSUE_TEMPLATE/ (contributor safety checklist), root scripts and their shebangs.
- Rationale: Matches spec's "user-facing documentation (README, workflow.md, model-library.md, quickstarts, and any usage examples)" + clarifications. Quickstarts here mean the validation guides, but the spirit is end-user quickstarts; the per-feature ones are dev artifacts. Keeps PR focused and avoids breaking 100+ task cross-refs.
- Alternatives considered:
  - Broad edit of all .md including specs: rejected (noise, drift in historical accuracy).
  - Only README + constitution: rejected (US2 requires consistent highlighting across workflow and model docs).

### Decision: `hf-select-download` -> `comfygo models enrich` in prose
- Change all user examples of `scripts/hf-select-download ...` (and variants with resume, cd + invoke) to the equivalent `comfygo models enrich ...` (the dispatch in comfy-local already strips the subcommand and forwards args + uses uv run --no-project).
- Update surrounding text: refer to "the `comfygo models enrich` helper (invokes the HF/Civitai enrichment tool)" or keep "model enrichment helper" and show the comfygo form.
- Keep the `scripts/hf-select-download` file and its direct docs only as "advanced / non-direnv bootstrap" note.
- Rationale: `comfygo models enrich` is already the surface added in 004 for enrichment (T058, FRs), and `comfygo models --help` / top level will surface it. Using it in docs builds the muscle memory for the single entry point. Matches "enrich" language in workflow end section and 004 spec.
- Alternatives: Keep documenting the hyphenated script as canonical: would directly violate FR-003 / SC-002 and the "remember one thing" goal.

### Decision: Bootstrap / power-user sections (patch apply, refresh, install wrappers)
- Retain the `COMFYUI_DIR=... ./scripts/xxx.sh` and `COMFY_CLI_DIR=...` forms under explicit "Initial bootstrap (before direnv / PATH)", "When the comfy-cli local-nodes patch is not yet applied", or "Contributor / repo maintenance" headings.
- Immediately after or in the same section, show the preferred `comfygo sync`, `comfygo refresh-upstreams`, `comfygo patch-cli`, `comfygo patch-comfyui`, `comfygo update`, `comfygo install` once the repo direnv has added scripts/ to PATH.
- Add a short note: "The repo `.envrc` puts `scripts/` on PATH so plain `comfygo` works; direct script calls remain supported for automation that does not assume direnv."
- Rationale: Some flows are literally required before `comfygo` can be the facade (e.g. applying the patch that adds `local-nodes` subcommand to comfy itself). Hiding them would break first-time setup instructions. But primary narrative must always lead with the single entry point.
- Alternatives: Remove all direct script examples: rejected (would make bootstrap impossible to document).

### Decision: Constitution reinforcement (no new top-level principle)
- Add 1-2 paragraphs + a bullet list under existing **III. Safe Daily Operation** (after the current "The normal daily command is `comfygo`." sentence).
- Text (draft):
  > The single entry point principle reinforces this: all user-facing documentation, examples, quickstarts, README flows, and daily guidance MUST present `comfygo` (and its subcommands such as `comfygo doctor`, `comfygo models enrich`, `comfygo sync`) as the one command users need to remember and type. Direct paths to `scripts/comfy-local`, `scripts/hf-select-download`, `scripts/update-from-upstreams.sh`, etc. are implementation details. They belong in "For contributors", "Quality gates", "Power users", or "Debugging" sections only.
  >
  > This reduces cognitive load for the solo SSH maintainer use-case and aligns governance (constitution) with the implemented facade (`scripts/comfygo` thin wrapper dispatching to `comfy-local`).
- Rationale: Clarifications explicitly say "reinforce under 'Safe Daily Operation' or a new note." Adding a numbered IV would be overkill for a clarification / highlighting feature (per Governance section, clarifications are PATCH). Strengthens existing text without weakening any principle.
- Version impact: Will require PATCH bump on the constitution (1.2.0 → 1.2.1) when the amendment is made, per "Clarifications, rewording, and non-semantic refinements require a PATCH version bump."
- Alternatives considered: New top-level "X. Single Entry Point" principle: rejected (too heavy for this scope; the goal is already implied by III and the 004 work).

### Decision: No new code changes required (per spec assumptions)
- The `comfygo` entry point + subcommand surface (including models enrich delegation) is already complete from prior features (004 in particular).
- This feature is purely alignment of docs + constitution.
- Any incidental fixes (e.g. making sure `comfygo --help` / usage() text is complete and accurate) are in-scope only if discovered during doc review; otherwise deferred or noted as non-goals.
- uv-first, secret-safety, etc. already enforced by existing code.

### Decision: Validation approach for the feature (feeds quickstart)
- Primary proof: a person who has only read the updated README or workflow.md top sections can name `comfygo` as the command for launch, doctor, model enrichment, sync, and patching flows.
- Mechanical checks (in quickstart): greps that forbid bare `scripts/hf-select-download`, `./scripts/update-from-upstreams.sh` etc. in the bodies of primary usage examples (outside explicit dev sections); `comfygo` appears first in command maps and daily-use lists.
- Manual: scan for "lower-level", "the script", "direct" language that might still teach multiple entry points.

### Other notes
- Branch protection / changelog / Codacy gates remain untouched by this plan (no code).
- The current plan.md in 005/ was a template; this research + subsequent design artifacts (data-model, contracts, quickstart) + edits to plan.md complete Phase 0/1.
- After plan, the natural next is `/speckit-tasks` (to produce tasks.md), then implement the doc edits (small, reviewable), run quality gates (even for docs: the verify script includes markdownlint etc.), then amend constitution + bump its patch version + update CHANGELOG.md per VIII.

**Output of research**: All NEEDS CLARIFICATION resolved (none existed in spec). Concrete edit targets and wording guardrails captured for Phase 1 artifacts.
