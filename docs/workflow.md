# Workflow

## Daily Use

1. Edit vendored custom node files in this repository.
2. Commit the change here.
3. Sync into the ComfyUI workspace:

   ```bash
   COMFYUI_DIR=/path/to/ComfyUI ./scripts/install-to-comfyui.sh
   ```

4. Launch ComfyUI with the synced copy:

   ```bash
   COMFYUI_DIR=/path/to/ComfyUI ./scripts/comfy-launch-with-local-nodes.sh -- --listen 127.0.0.1 --port 8188
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
