# Contracts: Single Entrypoint CLI (Documentation & Governance)

## Purpose
This contract defines the required shape of user-facing documentation and constitution text so that `comfygo` is the single memorable entry point (FR-001–FR-005, US1–US2, SC-001–SC-004).

It is a documentation/governance contract, not a new runtime interface. The runtime entry point (`scripts/comfygo` → `scripts/comfy-local`) already exists and is assumed stable.

## Documentation UX Contract

### Primary Command Surface
- The first command shown for daily operation in any user-facing document MUST be `comfygo` (or `comfygo <subcommand>`).
- `comfygo --help` (and the usage text emitted by the wrapper) is the canonical discoverability surface.
- Subcommand examples are written as:
  ```bash
  comfygo
  comfygo doctor
  comfygo models -f Qwen-Image
  comfygo models enrich owner/model --package-name Foo
  comfygo models reconcile -f Foo --apply
  comfygo sync
  comfygo refresh-upstreams
  comfygo patch-cli
  comfygo patch-comfyui
  comfygo restart
  ```
- The word "the normal daily command" or "the one command to remember" MUST be associated with `comfygo` in top-level sections (README "Sync To ComfyUI", workflow "Daily Use", constitution III).

### De-emphasis of Internal Wrappers
Direct script paths (`scripts/...`, `./scripts/...`, full `COMFY*_DIR=... ./scripts/...`) are permitted **only** under these explicit section headings (or equivalents):
- "Quality Gates (Mandatory Before Commit/Push)"
- "For Contributors"
- "Power users / bootstrap (before direnv)"
- "Internal implementation" / "Debugging"
- "When the comfy-cli local-nodes patch has not been applied yet"
- "Lower-level / direct script (advanced)"

In all other prose and example blocks that describe normal use (launch, enrich, doctor, reconcile, sync, patching after initial setup, model library maintenance), the direct forms are forbidden.

### Specific Renames Required in User Surfaces
- `scripts/hf-select-download ...` → `comfygo models enrich ...` (all package, resume, and cd+invoke forms in README + docs/model-library.md + workflow enrichment examples).
- `./scripts/update-from-upstreams.sh` → `comfygo refresh-upstreams` (primary), direct form only under "Updating Upstream Node Code" or contributor note.
- `COMFYUI_DIR=... ./scripts/install-to-comfyui.sh` → `comfygo sync` (primary); direct kept only for dry-run bootstrap illustration.
- Legacy comfy-launch/update/install-with-local-nodes.sh examples → note that `comfygo` (once patched) or the patched `comfy` subcommands are preferred; direct forms only for "Comfy CLI Wrappers (bootstrap)" section.
- "The lower-level sync script is still available" language must be followed by "Prefer `comfygo sync`."

### Quickstarts and Validation Guides
Per-feature `specs/*/quickstart.md` and contracts are implementation records. They may continue to use the exact harness commands required for reproducible test execution (including `UV_CACHE_DIR=... scripts/comfygo ...` or direct scripts when testing isolation). They are out of scope for the "new user only sees comfygo" rule.

## Constitution Alignment Contract
- The text under **III. Safe Daily Operation** (or a clearly related subsection) MUST explicitly name `comfygo` as the single entry point and state that docs/examples must lead with it.
- The reinforcement is a clarification (PATCH version bump on constitution per Governance rules), not a new numbered principle.
- No weakening of I (Vendored), II (Explicit Refresh), V (Secret Safety), VI (uv-first), VII (Verifiable), VIII (Changelog), or IX (Branch Protection).

## Verification of the Contract (see quickstart.md)
- Grep-based mechanical checks on the allowed user surfaces for stray direct script invocations in non-bypass sections.
- Manual review that `comfygo` appears as the lead command in command maps, daily-use lists, and model-enrichment flows.
- Constitution text contains the required reinforcement language (search for "single entry point principle" or equivalent after edit).
- A reader who has seen only the top-level README or "Daily Use" can answer "what is the one command I run for normal work?" with `comfygo` without consulting other files.

## Non-Goals (out of scope for this contract)
- Changing behavior or adding new subcommands (already covered by 004 and earlier).
- Renaming files on disk.
- Forcing every internal test or CI invocation to drop the `scripts/` prefix.
- Updating every historical task comment or spec cross-reference.

## Related
- Feature spec: [spec.md](../spec.md)
- Data model: [data-model.md](../data-model.md)
- Implementation plan: [plan.md](../plan.md)
- Source of the facade: `scripts/comfygo`, `scripts/comfy-local` (usage text and dispatch)
