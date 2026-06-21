#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
comfyui_dir="${COMFYUI_DIR:-}"
dry_run=0
apply_patches=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --comfyui-dir)
      comfyui_dir="$2"
      shift 2
      ;;
    --dry-run)
      dry_run=1
      shift
      ;;
    --no-patches)
      apply_patches=0
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "$comfyui_dir" ]]; then
  echo "COMFYUI_DIR is required, for example: COMFYUI_DIR=/path/to/ComfyUI $0" >&2
  exit 2
fi

source_dir="$repo_dir/custom_nodes"
target_dir="$comfyui_dir/custom_nodes"

if [[ ! -d "$source_dir" ]]; then
  echo "Vendored custom_nodes directory not found: $source_dir" >&2
  exit 2
fi

if [[ ! -d "$comfyui_dir" ]]; then
  echo "ComfyUI directory not found: $comfyui_dir" >&2
  exit 2
fi

rsync_flags=(
  -rlptD
  --delete
  --exclude=.git/
  --exclude=__pycache__/
  --exclude='*.pyc'
  --exclude='*.pyo'
  --exclude='.tracking'
  --exclude='*.log'
  --exclude='*.sqlite'
  --exclude='*.db'
  --exclude='.env'
  --exclude='.env.*'
  --exclude='*.token'
  --exclude='system_prompts_user.json'
  --exclude='custom_models.json'
  --exclude='debug_config.json'
  --exclude='debug_*.json'
  --exclude='*.safetensors'
  --exclude='*.ckpt'
  --exclude='*.pt'
  --exclude='*.pth'
  --exclude='*.bin'
  --exclude='*.gguf'
  --exclude='*.onnx'
  --exclude='tests/'
  --exclude='testframework/'
  --exclude='test*.py'
  --exclude='pytest.ini'
  --exclude='requirements-dev.txt'
  --exclude='conftest.py'
)

if (( dry_run )); then
  rsync_flags+=(--dry-run --itemize-changes)
fi

mkdir -p "$target_dir"

shopt -s nullglob
for source in "$source_dir"/*; do
  name="$(basename "$source")"
  if [[ -d "$source" ]]; then
    mkdir -p "$target_dir/$name"
    rsync "${rsync_flags[@]}" "$source/" "$target_dir/$name/"
  else
    rsync -rlptD "$source" "$target_dir/"
  fi
done

if (( apply_patches )); then
  if (( dry_run )); then
    echo "Dry run: skipping patch application"
  else
    COMFYUI_DIR="$comfyui_dir" "$repo_dir/scripts/apply-comfyui-patches.sh"
  fi
fi

echo "Vendored custom nodes synced to $target_dir"
