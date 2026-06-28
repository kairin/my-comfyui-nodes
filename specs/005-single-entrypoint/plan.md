# Implementation Plan: Single Entrypoint CLI

**Branch**: `005-single-entrypoint` | **Date**: 2026-06-22 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-single-entrypoint/spec.md` (user request to ensure one memorable entry point `comfygo` is highlighted everywhere in docs + constitution, with subcommands acceptable; primarily docs/governance alignment on top of the existing `scripts/comfygo` facade from prior features).

## Summary

Ensure a single memorable entry point (`comfygo`, with subcommands) is the only thing users need to remember for daily ComfyUI operations (launch, patching, enrichment via Civitai/HF, doctor/diagnostics, sync, etc.).

Primary requirement (from spec): All user-facing documentation (README, docs/workflow.md, docs/model-library.md, quickstarts, examples) and the project constitution MUST consistently highlight `comfygo` (or `comfygo <sub>`) as the canonical command. Internal implementation scripts remain for power users and bootstrap but are de-emphasized and never presented as the primary interface in normal flows (FR-001..FR-005, US1/US2, SC-001..SC-004).

Technical approach (from research + spec assumptions):
- No new runtime code or subcommand behavior is required (the thin `scripts/comfygo` wrapper + `comfy-local` dispatch + `models enrich` forwarding already exist and satisfy the "one command" surface).
- Updates are documentation + governance only: rewrite examples in the three primary user docs to lead with `comfygo`; add explicit reinforcement paragraph(s) under constitution III. Safe Daily Operation; update quickstarts/contracts/data-model in this spec dir for the docs/governance feature.
- Research identified exact bypass sites (hf-select-download, update-from-upstreams direct, legacy comfy-* wrappers, "lower-level sync script" language) and decided on scope (user tutorials only; leave specs/*, AGENTS, issue templates, quality scripts as-is).
- Post-edit: run quality gates (verify-quality.sh covers markdownlint etc.), add CHANGELOG entry (VIII), PATCH-bump constitution version, run agent-context update.
- Aligns with constitution principles (no violations); supports the SSH solo maintainer use-case that motivated the whole 001-004 series.

See generated [research.md](research.md) for detailed decisions, alternatives, and rationale.

## Technical Context

**Language/Version**: Bash (orchestration wrappers) + Python 3.11+ (model helpers + comfygo_model_registry custom node). uv-first for all Python/comfy-cli invocations.

**Primary Dependencies**: direnv (env loading), uv (runner + env), optional: gh (protection checks in doctor), tmux (for launch policy in 004). No new runtime deps for this feature.

**Storage**: Filesystem only (no DB). Docs are plain markdown + the constitution YAML-like header comments. Local state (COMFYUI_DIR etc.) lives in ignored .env* files only.

**Testing**:
- Manual + grep validation of docs (see quickstart.md scenarios).
- Existing pytest on the registry (unchanged).
- ShellCheck / bash -n on any touched scripts (none expected).
- Full `./scripts/verify-quality.sh` (includes markdownlint) before any commit.

**Target Platform**: Linux servers (primary SSH single-terminal use case from 004). Docs apply to any shell that can run the wrappers.

**Project Type**: Documentation + governance alignment feature for an existing CLI facade tool (`comfygo`). The repo is a hybrid: vendored custom nodes (many third-party) + owned Python package under custom_nodes/comfygo_model_registry + bash scripts + patches + speckit specs.

**Performance Goals**: N/A (no runtime perf change).

**Constraints**:
- Must not break existing direct script invocations (power users, bootstrap before direnv, CI harnesses, and historical specs rely on them).
- "Documentation" scope per clarifications + spec: README, workflow.md, model-library.md, usage examples, constitution. Feature quickstarts and AGENTS/issue templates are contributor artifacts.
- uv-first, secret-safety, no committed tokens/paths/weights (already true; this feature adds zero new scripts).
- Preserve all prior speckit artifacts (001-004).
- The single entry point facade (`scripts/comfygo`) is already implemented; this feature only aligns the "front of mind" presentation.

**Scale/Scope**: Very small. 3 user doc files + 1 constitution file + generated speckit design artifacts (research, data-model, contracts, quickstart, updated plan). No source tree changes to scripts/ or custom_nodes/.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Vendored source of truth (I)**: PASS. This plan touches only docs and the constitution file in the vendored repo. No custom-node or patch behavior is altered. Internal wrappers stay in `scripts/` as the implementation details (per FR-005).
- **Explicit upstream refresh (II)**: PASS. No changes to launch/sync vs. upstream logic. Refresh flows are only re-documented under the `comfygo` surface (the existing `comfygo refresh-upstreams` path is unchanged).
- **uv-first execution (VI)**: PASS. No new Python or comfy-cli commands are introduced in this plan. All existing dispatch paths (including `comfygo models enrich`) already use `uv run --no-project ...`. Documentation updates will continue to show uv-first forms where relevant.
- **Public repo and secret safety (V)**: PASS. Pure documentation/governance change. No tokens, paths, weights, or runtime artifacts are added to any file.
- **Verifiable runtime behavior (VII)**: PASS (by reference). The feature adds no new runtime mutations. Existing `comfygo doctor`, status, and the quickstart validation scenarios (doc greps + new-user simulation) provide the verification surface. The quickstart.md explicitly cross-references the contracts for mechanical + manual checks.
- **Changelog (VIII)**: PASS (enforced). User-facing documentation change + constitution clarification requires an entry in root CHANGELOG.md (under a new dated section). This will be created during implementation.
- **Branch protection & safety nets (IX)**: PASS. No CI / protection / Codacy changes. The existing "run `./scripts/verify-quality.sh` before commit" rule (already in AGENTS, workflow, README) continues to apply; the verify script itself will catch any markdown issues introduced.

**Gate verdict (pre-Phase 0)**: PASS — design stays aligned with all principles. No Complexity Tracking table needed.

**Post-Phase 1 re-check**: CONFIRMED PASS (2026-06-22). All supporting artifacts (research.md, data-model.md, contracts/README.md, quickstart.md) generated during initial /speckit-plan execution. Subsequent /speckit-tasks generated 27 tasks.md (US1/US2 phases, no new runtime code per spec assumptions). Design remains fully aligned: strengthens III. Safe Daily Operation, no violations of any principle (I-IX), no Complexity Tracking needed. Gate still PASS after tasks generation.

## Project Structure

### Documentation (this feature)

```text
specs/005-single-entrypoint/
├── spec.md
├── plan.md                 # This file (filled by /speckit-plan)
├── research.md             # Phase 0 (generated)
├── data-model.md           # Phase 1 (generated)
├── quickstart.md           # Phase 1 (generated)
├── contracts/
│   └── README.md           # UX / documentation contract (generated)
├── checklists/
│   └── requirements.md     # (pre-existing, passed)
└── tasks.md                # Phase 2 (NOT created by /speckit-plan; use /speckit-tasks)
```

### Source Code (repository root)

No structural changes. The single entry point facade already exists:

```text
scripts/
├── comfygo                 # thin dispatcher (the single entry point users remember)
├── comfy-local             # main implementation (settings, launch seq, doctor, models dispatch, etc.)
├── hf-select-download      # uv wrapper (power-user form; primary promoted form is comfygo models enrich)
├── hf_select_download.py   # the enrichment/download logic
├── comfygo-models.sh       # registry CLI wrapper
└── ... (other internal: update-from-upstreams.sh, apply-*.sh, install-to-comfyui.sh, verify-quality.sh, git-with-verify.sh, etc.)

custom_nodes/
└── comfygo_model_registry/ # owned Python package (cli, models, descriptor, gc, etc.)

docs/
├── workflow.md
└── model-library.md

README.md
AGENTS.md                   # (speckit marker will be updated to this plan)
.specify/memory/constitution.md
```

**Structure Decision**: This is a documentation + governance feature. Selected "Option 1 single project" with zero additions to the source tree. All work is edits to existing user-facing .md files + the constitution + the speckit design artifacts under specs/005-single-entrypoint/. The runtime dispatch tree (comfygo → comfy-local + sub-dispatch) is referenced but not modified.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No entries — Constitution Check passed with no violations (see above). This plan introduces no architectural complexity, new runtime surfaces, or deviations from uv-first / safety principles.

## Phases (per speckit-plan workflow)

**Phase 0 (research)**: Complete. See [research.md](research.md). All potential NEEDS CLARIFICATION areas (scope of "documentation", treatment of hf-select-download vs. models enrich, bootstrap vs. daily examples, constitution reinforcement location and version impact) were researched via file inspection + grep inventory of bypass sites. Decisions and alternatives documented. No unresolved items.

**Phase 1 (design & contracts)**:
- [research.md](research.md) generated.
- [data-model.md](data-model.md) generated (entities: SingleEntryPointCommand, DocumentationSurface, InternalWrapper + validation rules derived from FRs/clarifications).
- [contracts/README.md](contracts/README.md) generated (Documentation UX Contract + Constitution Alignment Contract + verification notes).
- [quickstart.md](quickstart.md) generated (6 scenarios: README leadership, workflow enrichment, model-library rename, constitution text, mechanical grep, new-user simulation; plus implementer checklist).
- Agent context updated (see below).
- This plan.md filled with Technical Context, Constitution Check (PASS), Project Structure, and cross-references.

**Post-design Constitution Check re-evaluation**: Still PASS. The design artifacts only codify the existing facade and the docs/constitution alignment requirements already stated in the feature spec. No new commands, no secret leakage, uv forms unchanged, verifiable via the new quickstart greps + simulation. Changelog (VIII) and gates (IX) explicitly called out as implementation obligations.

## Implementation Notes (high level)
- Primary work items (to be expanded by /speckit-tasks):
  - Edit README.md: command map, sync/refresh sections, wrappers section, lower-level script notes → all lead with comfygo; add "single entry point" callout.
  - Edit docs/workflow.md: daily use (already good), enrichment examples (change hf-select), upstream/patch sections (add comfygo forms + deprecate notes), issue template refs if needed.
  - Edit docs/model-library.md: all `scripts/hf-select-download` examples + prose → `comfygo models enrich` equivalents.
  - Edit .specify/memory/constitution.md: add reinforcement text under III. Safe Daily Operation per research decision + bump version to 1.2.1 (PATCH).
  - Add root CHANGELOG.md entry (user-facing doc + governance change for 005).
  - Run `./scripts/verify-quality.sh` (and pre-commit if installed) before commit.
  - Optionally update .github/ISSUE_TEMPLATE/ or AGENTS.md prose only if it improves consistency without harming contributor instructions (research recommends leaving most as-is).
- The `comfygo` usage text in scripts/comfy-local may receive a tiny polish pass if review shows subcommands are not fully listed, but this is secondary.
- All edits must keep the spirit of "internal scripts still work" (FR-005 / edge cases).

## Risks & Mitigations
- Risk: Over-editing specs or AGENTS.md pollutes history or breaks agent instructions. Mitigation: strict scope per research; only touch README + docs/*.md user sections + constitution.
- Risk: First-time bootstrap instructions become unusable if direct scripts are removed. Mitigation: explicit "bootstrap before direnv" / "legacy wrappers" sections retained with clear "prefer comfygo once set up" guidance.
- Risk: Constitution PATCH bump + CHANGELOG forgotten. Mitigation: explicit in quickstart implementer checklist + post-plan tasks.
- No security or secret risks (docs only).

## Verification Approach
See the generated [quickstart.md](quickstart.md) (scenarios 1-6 + mechanical greps + new-user simulation). These are sufficient to prove SC-001..SC-004 and the contracts without a live ComfyUI tree. After doc edits, re-run the greps and manual review before claiming completion.

## Next
1. `/speckit-tasks` completed (27 tasks generated in tasks.md: Phase 1 Setup, Phase 2 Foundational, Phase 3 US1 P1 MVP, Phase 4 US2 P2, Phase 5 Polish; full dependency/parallel/strategy sections; strict checklist format with file paths; MVP = US1).
2. Implement the doc/constitution edits per tasks.md (small, reviewable changes to README.md, docs/workflow.md, docs/model-library.md, constitution.md, CHANGELOG.md).
3. `./scripts/verify-quality.sh` (mandatory per AGENTS + constitution IX before any commit). Must pass with ✅ .
4. Update CHANGELOG.md + constitution version (to 1.2.1 PATCH).
5. Re-run quickstart.md scenarios (1-6) + new-user simulation + mechanical greps to validate SCs/FRs.
6. (Optional) `/speckit-analyze` + `/speckit-converge` to confirm no drift vs spec/plan/tasks.
7. Commit (only after gate ✅) and push. Then test the app with real `comfygo` (launch, models enrich, doctor, etc.) under direnv + COMFYUI_DIR.

This plan (refreshed on re-invocation of /speckit-plan post-tasks) stays at the level of the approved speckit flow. Concrete edits are driven by tasks.md. The 005 feature completes the "one command to remember" UX goal that was the through-line of the 001-004 series and the constitution. All design artifacts (plan, research, data-model, contracts, quickstart, tasks) now present and consistent.
