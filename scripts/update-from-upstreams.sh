#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
upstreams="$repo_dir/UPSTREAMS.tsv"
tmp_dir="$(mktemp -d)"

cleanup() {
  rm -rf "$tmp_dir"
}
trap cleanup EXIT

if [[ ! -f "$upstreams" ]]; then
  echo "Missing $upstreams" >&2
  exit 2
fi

while IFS=$'\t' read -r folder url source ref notes; do
  [[ -z "${folder:-}" || "$folder" == \#* ]] && continue
  [[ -z "${url:-}" ]] && continue

  echo "Updating $folder from $url"
  clone_dir="$tmp_dir/$folder"
  git clone --depth 1 "$url" "$clone_dir"

  mkdir -p "$repo_dir/custom_nodes/$folder"
  rsync -rlptD --delete \
    --exclude=.git/ \
    --exclude=__pycache__/ \
    --exclude='*.pyc' \
    --exclude='*.pyo' \
    --exclude='.tracking' \
    --exclude='*.log' \
    --exclude='*.sqlite' \
    --exclude='*.db' \
    --exclude='.env' \
    --exclude='.env.*' \
    --exclude='*.token' \
    --exclude='system_prompts_user.json' \
    --exclude='custom_models.json' \
    --exclude='debug_config.json' \
    --exclude='debug_*.json' \
    --exclude='*.safetensors' \
    --exclude='*.ckpt' \
    --exclude='*.pt' \
    --exclude='*.pth' \
    --exclude='*.bin' \
    --exclude='*.gguf' \
    --exclude='*.onnx' \
    "$clone_dir/" "$repo_dir/custom_nodes/$folder/"
done < "$upstreams"

echo "Upstream refresh complete. Review with: git diff"
