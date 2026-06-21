#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
comfy_cli_dir="${COMFY_CLI_DIR:-$HOME/Apps/comfy-cli}"
comfyui_dir="${COMFYUI_DIR:-}"

if [[ -z "$comfyui_dir" ]]; then
  echo "COMFYUI_DIR is required, for example: COMFYUI_DIR=/path/to/ComfyUI $0" >&2
  exit 2
fi

cd "$comfy_cli_dir"
uv run comfy --workspace "$comfyui_dir" update comfy "$@"

COMFYUI_DIR="$comfyui_dir" "$repo_dir/scripts/install-to-comfyui.sh"

# T012: re-patch after update step (part of sequential "get up to date")
# Re-apply known patches using manifests (see T009/T010)
COMFYUI_DIR="$comfyui_dir" "$repo_dir/scripts/apply-comfyui-patches.sh" || true
COMFY_CLI_DIR="$comfy_cli_dir" "$repo_dir/scripts/apply-comfy-cli-patches.sh" || true
echo "Re-patch after update attempted (use manifests for drift detection in future)."
