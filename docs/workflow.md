# Workflow

## Daily Use

0. Let direnv load your local paths:

   ```bash
   direnv allow
   ```

1. Launch the current preferred setup:

   ```bash
   comfygo
   ```

2. Check the setup without launching:

   ```bash
   comfygo doctor
   ```

   If a workflow cannot find a model you believe is installed, search by name
   and model category:

   ```bash
   comfygo models -f Qwen-Image
   ```

   To make a full model folder visible to category-specific ComfyUI nodes
   without copying model files:

   ```bash
   comfygo models reconcile -f Qwen-Image --apply
   comfygo restart
   ```

   The normal `comfygo` launch and `comfygo restart` path also reconciles
   generated model views automatically for identifiable full model folders.

3. Add new HF models in canonical model folders:

   **Use the single entry point:** `comfygo models enrich ...` (the model enrichment helper; supports HF git-clone or loose files + optional Civitai when token present).

   ```bash
   comfygo models enrich owner/model-repo \
     --models-root "$COMFYUI_MODELS_DIR" \
     --package-name Model-Folder-Name
   comfygo models reconcile --apply
   ```

   (Direct `scripts/hf-select-download` remains for bootstrap/non-direnv; prefer `comfygo models enrich` for normal use per single entry point.)

4. If a shell under the ComfyUI runtime root needs Hugging Face or other local

## Local Quality Gates (Mandatory Before Commit/Push)

**Goal**: Ensure code passes Codacy *before* it ever leaves your machine. This prevents sloppy commits, failed merges, wasted GitHub Actions minutes, and Codacy token usage.

### Setup (one time)
```bash
# Install pre-commit (uv-first)
uv tool install pre-commit
pre-commit install   # installs git hooks

# Make the full verifier executable (already done in repo)
chmod +x scripts/verify-quality.sh
```

### Daily workflow
1. Make your changes.
2. **Before committing**, the pre-commit hooks will run on `git commit`:
   - Ruff (lint + format)
   - ShellCheck (for scripts/)
   - Bandit (security)
   - Relevant tests
   - Basic hygiene
3. Additionally (or if hooks skipped), run the full local verifier that closely matches what Codacy will execute:
   ```bash
   ./scripts/verify-quality.sh
   ```
4. Only if the above passes:
   ```bash
   git commit -m "..."
   git push
   ```
5. CI (Codacy) will then run as the final safety net (should be green).

### What the verifier checks (Codacy-equivalent)
- Ruff (primary Python linter/formatter we have enabled in Codacy)
- ShellCheck
- Bandit security
- Registry tests
- Codacy CLI partial scan (when possible)
- Other hygiene

If this script passes locally, the Codacy workflow in CI should pass.

**Never push code that fails the local verifier.** If you do, you'll see the same failures (or worse) in the PR and waste resources.

See also:
- `.pre-commit-config.yaml`
- `scripts/verify-quality.sh`
- `AGENTS.md` (Quality Gates section)
- Constitution Principle on verifiable behavior

## Solo Maintainer: Good-Enough Branch Protection & Safety Nets

This project is maintained by a single developer. Overly strict rules (multiple required human reviews) would be overkill and block work.

**Recommended "good enough" baseline (see GitHub branch protection on `main` + Codacy Gate Policy):**

- Require pull requests before merging to `main` (no direct pushes).
- Require status checks to pass (at minimum the Codacy Analysis check from `.github/workflows/codacy-analysis.yml`).
- Required approving reviews: 0 (self-approval by owner is acceptable).
- Require branches to be up-to-date before merging.
- Require conversation resolution on PRs.
- Block force pushes and branch deletions: enabled.
- Enforce admin restrictions: off (solo flexibility).
- Linear history: optional.

**Codacy side:**
- Gate Policy + key tools (Bandit, Pylint/Prospector, ShellCheck, Trivy/Checkov, markdownlint, etc.) stay enabled.
- The analysis check is required (catches issues early via PR feedback).
- Grade and goals are guidance/visibility tools. Do not make low grade a hard merge blocker while solo (adjust if the project grows).
- Use issues and the gate for technical debt tracking.

These provide real safety nets (CI must run, can't silently break main) without slowing a solo maintainer.

Related issues: #95 (protection), and tasks T004/T005 in `specs/004-comfygo-patched-tmux/tasks.md`.

See also the updated constitution (Principles VIII + IX) and root `CHANGELOG.md`.

## Protection Verification (as of 2026-06-21, updated on feature branch)

Current GitHub main protection (from `gh api`):
- required_pull_request_reviews: 0 (self-approval allowed), dismiss_stale_reviews: true, conversation_resolution: true
- required_status_checks: strict=true, contexts=["analysis"]
- enforce_admins: false, allow_force_pushes: false, allow_deletions: false, required_linear_history: false

Matches "good enough" solo baseline in constitution IX and task T004/T005.

- Codacy: Gate Policy active, analysis check required in GitHub. Grade/goals for visibility only.

See related: constitution Principles VIII + IX, tasks T004/T005/T034 in 004, issue #95.

Run `gh api repos/kairin/my-comfyui-nodes/branches/main/protection` or `comfygo doctor --protection` (to be added in T007) for checks.

## Changelog Maintenance

See root `CHANGELOG.md`. All user-facing and significant changes are recorded there per constitution Principle VIII.
   tokens, generate the runtime direnv scope once:

   ```bash
   comfygo runtime-envrc
   cd /path/to/comfyui-runtime-root
   direnv allow
   ```

   Do not commit runtime `.envrc` files from the runtime root; they are
   machine-local state. `comfygo` imports this runtime direnv environment before
   launching or restarting ComfyUI, so token changes require a backend restart.

5. If you edited vendored custom node files, commit the change here.
6. Sync into the ComfyUI workspace without launching:

   ```bash
   comfygo sync
   ```

## Updating Upstream Node Code

**Primary (normal use):** `comfygo refresh-upstreams`, `git diff`, review, commit, then `comfygo sync`.

1. Refresh vendored node folders (direct form for non-direnv/bootstrap):

   ```bash
   ./scripts/update-from-upstreams.sh
   ```

2. Review the changes:

   ```bash
   git diff
   ```

3. Resolve conflicts or restore files as needed.
4. Commit the result.
5. Sync into ComfyUI (use `comfygo sync`).

## ComfyUI Core Patches

**Primary (normal use after initial setup):** `comfygo patch-comfyui`.

ComfyUI core changes are kept as patch files in `comfyui-patches/`. Apply them
with (bootstrap / when patch not yet in runtime):

```bash
COMFYUI_DIR=/path/to/ComfyUI ./scripts/apply-comfyui-patches.sh
```

If a patch no longer applies after updating ComfyUI, review the upstream change
and refresh the patch from the live ComfyUI checkout. Use `comfygo patch-comfyui` for the single entry point path once set up.

## Comfy CLI Patch

**Primary (normal use after setup):** `comfygo patch-cli`.

The local comfy-cli integration is stored as a patch under `comfy-cli-patches/`
after it is generated. The wrapper scripts in this repo do not depend on that
patch, so they keep working even when comfy-cli is reset or updated.

Apply the patch to a local comfy-cli checkout with (or use `comfygo patch-cli`):

```bash
COMFY_CLI_DIR=/path/to/comfy-cli ./scripts/apply-comfy-cli-patches.sh
```

## Issue Reporting

Use `.github/ISSUE_TEMPLATE/` for bug reports and feature requests.

When filing, reference:
- Relevant tasks from `specs/004-comfygo-patched-tmux/tasks.md`
- Constitution principles (e.g. VIII Changelog, IX Branch Protection, I Vendored Source of Truth)
- Confirmation that quality gates were run (`./scripts/verify-quality.sh` green)

This supports solo-maintainer protections and clear tracking for the 004 feature (patching, tmux launch, enrichment).

### Enrichment examples (T063)
Example for HF git-clone + Civitai:
```
# with CIVITAI_TOKEN and HF_TOKEN in direnv
comfygo models enrich /path/to/hf-cloned-model
# or loose
comfygo models enrich /path/to/model.safetensors
```
Results in HF layout + civitai/ side folder + comfygo-model.json with source hf + civitai (if match), usable by registry.
See scripts/hf_select_download.py --help and spec Key Entities for the JSON shape.
Run after `comfygo` launch if COMFYGO_ENRICH_CIVITAI=1.
Basic on no token: local info only, no secrets.
