#!/bin/bash
# Smoke test for re-patch after simulated update (T060)
# Run with: bash scripts/test-repatch-smoke.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Repatch smoke test ==="

# require dirs from env or assume test
if [[ -z "${COMFYUI_DIR:-}" || ! -d "$COMFYUI_DIR" ]]; then
  echo "COMFYUI_DIR not set or not dir; skipping full smoke (use for manual)"
  echo "To simulate: touch a patched file in COMFYUI_DIR, run the update/patch, check drift message or restore."
  exit 0
fi

PATCHED_FILE="extensions/comfyui-patches/comfy-sd-qwen-image-vae.patch"  # example, adjust to actual
if [[ ! -f "$COMFYUI_DIR/$PATCHED_FILE" ]]; then
  echo "No patched file to simulate; skipping"
  exit 0
fi

# backup
cp "$COMFYUI_DIR/$PATCHED_FILE" /tmp/backup.patch

# simulate update (touch to change mtime or content lightly)
touch "$COMFYUI_DIR/$PATCHED_FILE"

echo "Simulated update on $PATCHED_FILE"

# run patch via local (or full sequence dry)
echo "Running patch check..."
bash -c "
source '$REPO_DIR/scripts/comfy-local'
patch_drift_check '$COMFYUI_DIR' '$REPO_DIR/comfyui-patches'
" || true

# restore
mv /tmp/backup.patch "$COMFYUI_DIR/$PATCHED_FILE"

echo "Smoke done - check output for drift detection and message per Error and Exit Contracts"
echo "For full: run with COMFYGO_ENRICH etc, verify no corrupt, message has historical name + edit instruction."