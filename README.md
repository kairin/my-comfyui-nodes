# my-comfyui-nodes

Vendored ComfyUI custom nodes and local patches for a preferred ComfyUI setup.

This repository is intended to be public. Do not commit API keys, model weights,
personal prompts, local paths with secrets, or runtime histories here.

## Codacy

This repo is configured with a Codacy CI analysis workflow at `.github/workflows/codacy-analysis.yml`.

**Important**: Codacy is a *final gate*, not the place to discover problems. All code must pass local quality checks *before* you commit or push.

### Local verification (required before commit/push)
See the detailed process in:
- `docs/workflow.md` → "Local Quality Gates (Mandatory Before Commit/Push)"
- `AGENTS.md` → "Quality Gates (Before ANY Commit or Push)"
- `.pre-commit-config.yaml`
- `scripts/verify-quality.sh`

Run these before every commit:
```bash
pre-commit run --all-files
./scripts/verify-quality.sh
```

This replicates (as much as possible) the tools Codacy runs (Ruff, Bandit, ShellCheck, tests, etc.). When local verification passes, the CI check should pass.

### CI setup
1. In Codacy, add the GitHub repository `kairin/my-comfyui-nodes`.
2. Generate a project token in Codacy.
3. Add it to this repository as GitHub secret `CODACY_PROJECT_TOKEN`.
4. Push a commit (or open a pull request) to trigger the analysis job.

The workflow expects `.codacy.yml` and runs on `main` and pull requests to `main`.

Branch protection requires the Codacy check to pass before merges.

## Layout

```text
custom_nodes/       Full vendored copies of selected custom nodes
comfyui-patches/   Patches for ComfyUI core
comfy-cli-patches/ Patches for the local comfy-cli fork
scripts/           Sync and wrapper scripts
docs/              Operational notes
UPSTREAMS.tsv      Upstream sources used to refresh vendored copies
```

## Source Of Truth

Edit custom node code in this repo first, then sync it into a ComfyUI workspace.
Do not edit your live ComfyUI `custom_nodes` directory directly unless you are
doing a temporary experiment.

```text
upstream creator repos
        -> this vendored repo
        -> ComfyUI custom_nodes runtime
```

## Sync To ComfyUI

For normal use, use the one-word launcher:

```bash
comfygo
```

It applies local integration where possible, syncs vendored nodes, applies
ComfyUI patches, and launches ComfyUI.

The same command also maps to the lower-level operations:

```bash
comfygo status
comfygo doctor
comfygo models -f Qwen-Image
comfygo models reconcile -f Qwen-Image
comfygo sync
comfygo restart
comfygo update
comfygo refresh-upstreams
comfygo runtime-envrc
```

Command map:

```text
comfygo                  daily path: patch comfy-cli if possible, sync nodes, apply ComfyUI patches, verify nodes, launch
comfygo doctor           verify paths, patches, uv, and expected custom nodes
comfygo models -f FILTER find installed model files and folder-category visibility
comfygo models reconcile -f FILTER [--apply]
                         self-identify full model folders and create compatibility views
comfygo sync             install/update the live custom_nodes copy from this repo
comfygo restart          restart a comfy-cli background ComfyUI, then launch
comfygo update           update ComfyUI through comfy-cli, then resync this repo
comfygo refresh-upstreams refresh vendored node sources from UPSTREAMS.tsv for review
comfygo runtime-envrc    write a machine-local direnv file for the ComfyUI runtime root
```

`comfygo` does not automatically pull upstream custom-node changes on every
launch. Use `comfygo refresh-upstreams`, review the diff, commit it, then run
`comfygo sync` or `comfygo`.

When a workflow says a model is missing, run `comfygo models -f <name-fragment>`.
ComfyUI nodes search specific model categories, so a full `diffusers/` folder
is not automatically visible to a node that asks for `diffusion_models/`.
Use `comfygo models reconcile -f <name-fragment> --apply` to create generated
symlink views under `.comfygo_views` without copying model files.
The normal `comfygo` launch and `comfygo restart` path runs this reconciliation
automatically for full model folders it can identify.

The longer-term model layout is descriptor-first: each installed model keeps a
personal folder with a `comfygo-model.json` descriptor, and `comfygo` generates
compatibility views for legacy category-based nodes. The vendored
`comfygo_model_registry` custom node registers those generated views at ComfyUI
startup. See
`docs/model-library.md`.

Preferred on a local machine: create an untracked `.envrc.local` file for
machine-local paths, then allow direnv for this repo.

```bash
COMFYUI_DIR=/path/to/ComfyUI
COMFY_CLI_DIR=/path/to/comfy-cli
```

```bash
direnv allow
```

The repo `.envrc` adds `scripts/` to `PATH`, so `comfygo` is available when
direnv has loaded this repo. The wrapper also falls back to `.env.local` if
direnv is not available.

To let shells opened under the ComfyUI runtime tree load the same local tokens
and path variables, generate a machine-local runtime `.envrc`:

```bash
comfygo runtime-envrc
cd /path/to/comfyui-runtime-root
direnv allow
```

The runtime root is the parent directory that contains the ComfyUI code and
models folders for the local machine. This file is local machine state and is
not part of this public repo. `comfygo`, `comfygo start`, and `comfygo restart`
import this runtime direnv environment before launching ComfyUI, so token
variables are available to the backend process after restart.

The lower-level sync script is still available:

```bash
COMFYUI_DIR=/path/to/ComfyUI ./scripts/install-to-comfyui.sh
```

This copies `custom_nodes/*` into `$COMFYUI_DIR/custom_nodes` and applies patches
from `comfyui-patches/`.

Dry run:

```bash
COMFYUI_DIR=/path/to/ComfyUI ./scripts/install-to-comfyui.sh --dry-run
```

## Comfy CLI Wrappers

These wrappers work even if the `comfy local-nodes` patch has not been applied to
your comfy-cli fork.

```bash
COMFYUI_DIR=/path/to/ComfyUI ./scripts/comfy-launch-with-local-nodes.sh -- --listen 127.0.0.1 --port 8188
COMFYUI_DIR=/path/to/ComfyUI ./scripts/comfy-update-with-local-nodes.sh
COMFYUI_DIR=/path/to/ComfyUI ./scripts/comfy-install-with-local-nodes.sh --restore --fast-deps --nvidia
```

If the comfy-cli patch is applied, you can also run:

```bash
uv run comfy --workspace /path/to/ComfyUI local-nodes sync --repo "$PWD"
```

Apply or re-apply the comfy-cli patch to a local comfy-cli checkout with:

```bash
COMFY_CLI_DIR=/path/to/comfy-cli ./scripts/apply-comfy-cli-patches.sh
```

## Refresh From Upstreams

Pull fresh upstream copies into this repo, then review and commit the resulting
diff:

```bash
./scripts/update-from-upstreams.sh
git diff
```

This does not push anything and does not touch the live ComfyUI runtime.

## Public Repo Rules

- Keep model files out of Git.
- Keep `.env*`, token files, local prompt/user files, logs, and caches out of Git.
- Keep upstream provenance in `UPSTREAMS.tsv`.
- Commit local changes here before syncing into the live ComfyUI workspace.
