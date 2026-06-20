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

3. If you edited vendored custom node files, commit the change here.
4. Sync into the ComfyUI workspace without launching:

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
