# Quickstart: Validating Single Entrypoint Alignment

**Feature**: 005-single-entrypoint

This guide provides runnable/manual validation scenarios that prove the documentation and constitution changes satisfy the single memorable entry point goal (US1, US2, FR-003, SC-001–SC-004) without requiring a full ComfyUI runtime.

See [data-model.md](data-model.md) and [contracts/README.md](contracts/README.md) for the entities and rules being validated. Do not treat these as the primary user quickstarts; they are verification for the docs/governance feature itself.

## Prerequisites
- Clean checkout of the feature branch (or main after merge).
- No special tokens or COMFYUI_DIR required (these are doc greps + reading).
- `grep`, a text editor or `cat`, and `bash` (for any `-n` syntax if touching scripts, but not needed here).

## Scenario 1: Top-level README leads exclusively with comfygo for daily flows (SC-002)
1. Open README.md.
2. Search the "Sync To ComfyUI" and "Command map" sections.
3. Verify the first commands shown are plain `comfygo`, `comfygo doctor`, `comfygo models ...`, `comfygo sync`, `comfygo refresh-upstreams`, etc.
4. In the "Comfy CLI Wrappers" and "Refresh From Upstreams" sections, confirm that any direct `./scripts/...` or `COMFY... ./scripts/...` appear only under bootstrap / legacy headings and are accompanied by a "prefer `comfygo ...`" note or equivalent.
5. Expected: No bare `scripts/hf-select-download`, `scripts/update-from-upstreams.sh` etc. in the primary narrative paragraphs.

Pass condition: A first-time reader sees only `comfygo` (and subcommands) as the way to launch, enrich, diagnose, and sync.

## Scenario 2: workflow.md daily use and enrichment use comfygo only (FR-003)
1. Open docs/workflow.md.
2. "Daily Use" section: first commands must be `comfygo`, `comfygo doctor`, `comfygo models reconcile...`.
3. Enrichment example (near end or the T063 section): must show
   ```bash
   comfygo models enrich /path/to/hf-cloned-model
   ```
   or equivalent (not the raw `scripts/hf-select-download`).
4. "Updating Upstream Node Code", patch apply, and quality gate sections may still reference `./scripts/verify-quality.sh`, `./scripts/update-from-upstreams.sh` etc. under the appropriate "contributor" or "quality" headings.
5. Expected outcome: the "how to add new HF models" and "reconcile" flows start with the single entry point.

## Scenario 3: model-library.md download flows go through the entry point
1. Open docs/model-library.md.
2. All "use the included helper" and "To resume..." code blocks that previously showed `scripts/hf-select-download` now show `comfygo models enrich ...` (with identical flags: `--package-name`, `--models-root`, `--resume-from`, `.` for prompt mode, etc.).
3. Prose still explains what the helper does, but the typed command is the `comfygo` form.
4. Legacy `scripts/comfygo-models.sh` examples (for GC/reconcile direct) are acceptable only if presented as "advanced / when you need the raw registry CLI".

## Scenario 4: Constitution names the single entry point (SC-003)
1. Open .specify/memory/constitution.md (or the rendered version if published).
2. Locate section **III. Safe Daily Operation**.
3. Confirm it contains language similar to:
   - "The normal daily command is `comfygo`."
   - A follow-up paragraph or bullets under the single entry point principle that says user-facing docs and examples must lead with `comfygo` and that direct script paths are implementation details / contributor-only.
4. Expected: the reinforcement is present; version has been bumped to 1.2.1 (or next PATCH) per Governance rules for clarifications.

## Scenario 5: Mechanical grep guard (can be added to verify-quality or a future lint)
Run from repo root:

```bash
# Forbidden in user surfaces outside bypass sections (illustrative; real check may be more nuanced)
grep -n 'scripts/hf-select-download\|scripts/update-from-upstreams.sh\|./scripts/install-to-comfyui.sh' \
  README.md docs/workflow.md docs/model-library.md || echo "No direct hf/update/install in primary user docs (good)"

# Positive: comfygo models enrich appears where enrichment is taught
grep -l 'comfygo models enrich' README.md docs/workflow.md docs/model-library.md || echo "Missing comfygo models enrich in at least one surface"
```

Pass when the first command reports no (or only expected) hits and the second finds the entry point form.

## Scenario 6: New-user simulation (manual, highest value)
1. Give a colleague (or yourself with fresh eyes) only this instruction: "Clone the repo, allow direnv, and tell me the one command you run every day to launch, check status, enrich a model, or reconcile views."
2. They should answer `comfygo` (or `comfygo doctor` / `comfygo models enrich`) without ever opening a script or having to remember `comfy-local`.
3. If they ask "which script?", the docs have failed the contract.

## Links to other artifacts
- Spec: [spec.md](spec.md)
- Plan: [plan.md](plan.md)
- Data model: [data-model.md](data-model.md)
- Contracts: [contracts/README.md](contracts/README.md)
- Checklist: [checklists/requirements.md](checklists/requirements.md)

## Post-change checklist for implementer
- [X] README.md updated + examples consistent
- [X] docs/workflow.md updated (hf-select, upstreams, patches)
- [X] docs/model-library.md updated (all download helper invocations)
- [X] constitution.md reinforced under III + PATCH version
- [X] CHANGELOG.md entry added (user-facing doc/governance change)
- [X] `./scripts/verify-quality.sh` run (markdownlint etc. will catch formatting) -- multiple runs, all ✅
- [X] Quickstart scenarios above re-run manually and pass (mechanical greps + positive checks executed; primary flows now lead with `comfygo`; bootstrap notes retained per contracts)
- [X] AGENTS.md speckit marker updated (via agent-context hook or script) to reference this plan (confirmed in T003 + re-runs)

These steps prove the feature without needing a live ComfyUI instance.
