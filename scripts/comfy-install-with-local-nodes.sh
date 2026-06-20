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
uv run comfy --workspace "$comfyui_dir" install "$@"

COMFYUI_DIR="$comfyui_dir" "$repo_dir/scripts/install-to-comfyui.sh"
