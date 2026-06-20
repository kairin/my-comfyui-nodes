#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
comfy_cli_dir="${COMFY_CLI_DIR:-}"

if [[ -z "$comfy_cli_dir" ]]; then
  echo "COMFY_CLI_DIR is required, for example: COMFY_CLI_DIR=/path/to/comfy-cli $0" >&2
  exit 2
fi

if [[ ! -d "$comfy_cli_dir/.git" ]]; then
  echo "COMFY_CLI_DIR is not a Git checkout: $comfy_cli_dir" >&2
  exit 2
fi

patch_dir="$repo_dir/comfy-cli-patches"
shopt -s nullglob
patches=("$patch_dir"/*.patch)

if (( ${#patches[@]} == 0 )); then
  echo "No patches found in $patch_dir"
  exit 0
fi

for patch in "${patches[@]}"; do
  if git -C "$comfy_cli_dir" apply --check "$patch"; then
    git -C "$comfy_cli_dir" apply "$patch"
    echo "Applied $(basename "$patch")"
  elif git -C "$comfy_cli_dir" apply --reverse --check "$patch"; then
    echo "Already applied $(basename "$patch")"
  else
    echo "Patch does not apply cleanly: $patch" >&2
    exit 1
  fi
done
