#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
comfyui_dir="${COMFYUI_DIR:-}"

if [[ -z "$comfyui_dir" ]]; then
  echo "COMFYUI_DIR is required, for example: COMFYUI_DIR=/path/to/ComfyUI $0" >&2
  exit 2
fi

if [[ ! -d "$comfyui_dir/.git" ]]; then
  echo "COMFYUI_DIR is not a Git checkout: $comfyui_dir" >&2
  exit 2
fi

patch_dir="$repo_dir/comfyui-patches"
shopt -s nullglob
patches=("$patch_dir"/*.patch)

if (( ${#patches[@]} == 0 )); then
  echo "No patches found in $patch_dir"
  exit 0
fi

for patch in "${patches[@]}"; do
  if git -C "$comfyui_dir" apply --check "$patch"; then
    git -C "$comfyui_dir" apply "$patch"
    echo "Applied $(basename "$patch")"
  elif git -C "$comfyui_dir" apply --reverse --check "$patch"; then
    echo "Already applied $(basename "$patch")"
  else
    echo "Patch does not apply cleanly: $patch" >&2
    exit 1
  fi
done
