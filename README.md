# my-comfyui-nodes

Vendored ComfyUI custom nodes and local patches for a preferred ComfyUI setup.

This repository is intended to be public. Do not commit API keys, model weights,
personal prompts, local paths with secrets, or runtime histories here.

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
