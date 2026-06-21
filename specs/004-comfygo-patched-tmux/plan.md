# Implementation Plan: Comfygo Patched Tmux Control

**Branch**: `004-comfygo-patched-tmux` | **Date**: 2026-06-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-comfygo-patched-tmux/spec.md` + detailed approved high-level plan in session (patching primary, up-front settings, sequential update/verify/tmux launch, patch resilience via versioned public docs, HF git-clone + Civitai enrichment, SSH single-terminal, privacy, preserve speckit work).

## Summary

Make the vendored base (custom_nodes + known patches) reliably patchable and re-patchable. Provide declarative up-front settings and a single launch command that does (update → verify → launch comfy in tmux) so the controlling shell stays free over SSH. Support preferred full HF git-clone folders + loose files with Civitai lookup + structured layout + rich descriptors. Add versioned patch manifests in the repo for resilience across updates, with clear user notification on mismatch. Keep all existing speckit artifacts.

## Technical Context

**Language/Version**: Bash (orchestration) + Python 3.11+ (registry + helpers). uv-first.

**Primary Dependencies**: Existing comfy-cli (patched), ComfyUI (checkout), direnv, tmux (for launch), requests or curl for Civitai/HF APIs (via tokens in direnv).

**Storage**: Filesystem (models, .comfygo_views, patch manifests, local config only).

**Testing**: pytest (registry), shell syntax checks, manual SSH simulation + end-to-end launch.

**Target Platform**: Linux server, headless, accessed over SSH.

**Constraints**:
- No secrets in committed files (patch docs, specs, issues).
- Must work from a single SSH terminal (tmux is the solution).
- Preserve existing speckit 001/002/003 artifacts and code.
- uv-first everywhere.
- The vendored content in this repo is the "base" that must be re-applicable.

## Constitution Check

- uv First: all new commands/scripts will use uv run.
- Vendored source of truth: the patches and custom_nodes here remain the source.
- Safe daily operation + explicit mutation: re-patch and enrichment are explicit or guarded.
- Public repo / secret safety: new docs and issues will be high-level only.
- Verifiable behavior: doctor/verify paths and new sequential logs provide visibility.

Gate verdict: PASS (design stays aligned).

## Project Structure (additions)

```text
specs/004-comfygo-patched-tmux/
├── spec.md
├── plan.md (this)
├── checklists/requirements.md
└── tasks.md (generated and maintained)

comfyui-patches/   # versioned .patch files + manifest.md per version for US1 re-patch (aligns with existing layout)
comfy-cli-patches/   # same for comfy-cli
# See tasks T009/T031 for manifest format and driver.

scripts/
  (enhance hf_select_download.py or add enrich-civitai)
  (enhance launch flow in comfy-local for tmux + sequential)
```

Existing structure is kept.

## Phases

**Phase 0**: Create this speckit spec + plan (done). Privacy review of all public artifacts.

**Phase 1**: Test leakage fix + small hardening (already started - excludes added to install script and patch).

**Phase 2**: Up-front settings loader + sequential launch driver with tmux integration in the main flow (comfy-local / wrappers).

**Phase 3**: Versioned patch manifests + re-patch / drift detection logic. User notification on mismatch.

**Phase 4**: Civitai + HF enrichment tool (extend hf helper) that produces rich JSON + side folders.

**Phase 5**: Optional discovery API surface + docs updates. Ensure everything is SSH + direnv clean.

**Phase 6**: speckit-tasks completion, public issues (high-level only), verification over simulated SSH.

## Key Implementation Notes (high level)

- New config loading for up-front settings: look in local direnv or a dotfile under the repo (ignored).
- tmux launch: use `tmux new-window -n comfyui -- "..."` or similar, record the target, provide helpers to send commands to it.
- Patch manifests: simple structured text/JSON listing touched paths + historical names. Driver compares current state to desired.
- Enrichment: new or extended Python helper that talks to Civitai (token from env), HF (token), does the move/skeleton work, writes the JSON using the existing schema + extra source fields.
- All changes must keep the existing `comfygo` / `comfy-local` entry points working.

## Risks & Mitigations

- tmux not present: clear error + hint.
- Breaking changes in Civitai/HF APIs: graceful fallback to local info + good error messages.
- Patch matching is heuristic: always provide human-override path and clear "update the patch" instructions.

## Verification Approach

See the approved high-level plan's Verification section (SSH simulation, sequential logs, tmux control retained, re-patch after simulated update, enrichment end-to-end, no private data leaked, existing harnesses still pass).

## Next

Run /speckit-tasks (done), /speckit-taskstoissues (done), and /speckit-implement (in progress). Turn high-level items into GitHub issues (public-safe wording).

This plan stays deliberately at the level of the approved session plan. Concrete code changes are driven by tasks.md (with post-implement updates for actual code state).

## Solo Maintainer Branch Protection & Safety Nets (Good Enough)

Because there is only one maintainer, "too much" protection would block progress.

**Recommended configuration (implemented/documented via T004/T005 + workflow.md updates):**

GitHub main:
- Require PRs (no direct pushes to main).
- Require status checks (Codacy Analysis at minimum).
- Required reviews: 0 (self-approval allowed for owner).
- Up-to-date branches + conversation resolution: required.
- Block force pushes + deletions: keep.
- Enforce admins: off.
- Linear history: optional.

Codacy:
- Gate Policy + core tools enabled.
- Make the analysis check *required* in GitHub (for visibility and early feedback).
- Grade/goals = guidance, not hard blockers while solo.

Current verified state (2026-06-21):
- Protection exists but currently has 0 reviews and no required checks (see gh api data).
- Codacy has active Gate Policy + many analyzers (PMD, Bandit, Trivy, Checkov, Pylint, ShellCheck, etc.) and runs on PR/push.
- Secret scanning + Dependabot already on.

See `docs/workflow.md` (new section) and GitHub issue #95 for details. This balances safety nets with practicality for a solo SSH-based server workflow.

Related constitution principles: VIII (Changelog) and IX (Branch Protection & Safety Nets).

Tasks referencing this: T004, T005 in `tasks.md`.
