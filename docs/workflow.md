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
   tokens, generate a machine-local runtime env file:

   ```bash
   comfygo runtime-envrc
   ```

## Workflow Debug (for agents)

Diagnose and patch ComfyUI **API-format** workflow JSON outside the browser.
Agents read structured JSON from stdout; the user **Loads** the fixed file in
ComfyUI (no canvas auto-push in v1).

```bash
# After a failed queue (preferred — uses ComfyUI history)
comfygo workflow diagnose --latest-error
comfygo workflow diagnose --prompt-id <uuid>

# Pre-queue / validation errors (workflow JSON on disk)
comfygo workflow diagnose --workflow /path/to/workflow_api.json
```

Parse stdout: `validation`, `dependencies`, `execution`, `remediation`.

Apply JSON patches (auto-checkpoint under `.comfygo_debug/checkpoints/`):

```bash
comfygo workflow apply --workflow broken.json --patch fixes.json --output fixed.json --validate
comfygo workflow diagnose --workflow fixed.json
```

Patch ops: `set_input`, `connect`, `add_node`, `remove_node`.

Rollback:

```bash
comfygo workflow checkpoint list
comfygo workflow checkpoint restore --id <checkpoint_id> --output restored.json
```

See `AGENTS.md` (Workflow Debug Protocol) and `specs/006-workflow-diagnose/`,
`specs/007-workflow-apply/`.

## Local Quality Gates (Mandatory Before Commit/Push)

**Goal**: Catch lint, formatting, security, and test issues *before* code ever leaves your machine. This prevents sloppy commits, failed merges, and wasted GitHub Actions minutes. There is no CI analysis workflow to catch problems after the fact — these local checks are the only quality gate.

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
3. Additionally (or if hooks skipped), run the full local verifier:
   ```bash
   ./scripts/verify-quality.sh
   ```
4. Only if the above passes:
   ```bash
   git commit -m "..."
   git push
   ```

### What the verifier checks
- Ruff (lint + format)
- ShellCheck
- Bandit security
- Registry tests
- Other hygiene

**Never push code that fails the local verifier.** There is no CI analysis to catch it afterward — a failing check means the code is not ready.

See also:
- `.pre-commit-config.yaml`
- `scripts/verify-quality.sh`
- `AGENTS.md` (Quality Gates section)
- Constitution Principle on verifiable behavior

## Solo Maintainer: Good-Enough Branch Protection & Safety Nets

This project is maintained by a single developer. Overly strict rules (multiple required human reviews) would be overkill and block work.

**Recommended "good enough" baseline (see GitHub branch protection on `main`):**

- Require pull requests before merging to `main` (no direct pushes).
- No required status checks — CI analysis was decommissioned on 2026-08-09;
  quality is enforced locally via pre-commit + `scripts/verify-quality.sh`
  (see above) before code is ever pushed.
- Required approving reviews: 0 (self-approval by owner is acceptable).
- Require branches to be up-to-date before merging.
- Require conversation resolution on PRs.
- Block force pushes and branch deletions: enabled.
- Enforce admin restrictions: off (solo flexibility).
- Linear history: optional.

This provides a real safety net (nothing merges to `main` without going
through a PR) without slowing a solo maintainer, and relies on the local
quality gates above rather than a CI status check.

Related issues: #95 (protection), and tasks T004/T005 in `specs/004-comfygo-patched-tmux/tasks.md`.

See also the updated constitution (Principles VIII + IX) and root `CHANGELOG.md`.

## Protection Verification

**Current** (since 2026-08-09): CI analysis (Codacy) was decommissioned, and
its required status check was removed from branch protection along with it.
`main` requires a pull request before merging but has no required status
checks; quality is enforced entirely by the local gates above.

Run `gh api repos/kairin/my-comfyui-nodes/branches/main/protection` to verify
the live configuration at any time.

<details>
<summary>Historical snapshot (as of 2026-06-21, superseded 2026-08-09)</summary>

GitHub main protection (from `gh api`) at the time:
- required_pull_request_reviews: 0 (self-approval allowed), dismiss_stale_reviews: true, conversation_resolution: true
- required_status_checks: strict=true, contexts=["analysis"]
- enforce_admins: false, allow_force_pushes: false, allow_deletions: false, required_linear_history: false

This matched the "good enough" solo baseline in constitution IX and task
T004/T005 at the time, including a required Codacy analysis status check
that has since been removed.

See related: constitution Principles VIII + IX, tasks T004/T005/T034 in 004, issue #95.

</details>

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
