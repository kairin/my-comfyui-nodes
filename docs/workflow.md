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

   ```bash
   scripts/hf-select-download owner/model-repo \
     --models-root "$COMFYUI_MODELS_DIR" \
     --package-name Model-Folder-Name
   comfygo models reconcile --apply
   ```

4. If a shell under the ComfyUI runtime root needs Hugging Face or other local
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

1. Refresh vendored node folders:

   ```bash
   ./scripts/update-from-upstreams.sh
   ```

2. Review the changes:

   ```bash
   git diff
   ```

3. Resolve conflicts or restore files as needed.
4. Commit the result.
5. Sync into ComfyUI.

## ComfyUI Core Patches

ComfyUI core changes are kept as patch files in `comfyui-patches/`. Apply them
with:

```bash
COMFYUI_DIR=/path/to/ComfyUI ./scripts/apply-comfyui-patches.sh
```

If a patch no longer applies after updating ComfyUI, review the upstream change
and refresh the patch from the live ComfyUI checkout.

## Comfy CLI Patch

The local comfy-cli integration is stored as a patch under `comfy-cli-patches/`
after it is generated. The wrapper scripts in this repo do not depend on that
patch, so they keep working even when comfy-cli is reset or updated.

Apply the patch to a local comfy-cli checkout with:

```bash
COMFY_CLI_DIR=/path/to/comfy-cli ./scripts/apply-comfy-cli-patches.sh
```
