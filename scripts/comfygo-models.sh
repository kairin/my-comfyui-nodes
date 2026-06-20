#!/usr/bin/env bash
# comfygo models — inspect and reconcile the ComfyUI model library.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Determine models directory: explicit flag > COMFY_MODELS_DIR >
# COMFYUI_DIR sibling models > COMFYUI_DIR/models > Python folder_paths fallback.
# This mirrors scripts/comfy-local's models_root() resolution while still
# allowing Python to use folder_paths.models_dir when no shell hint is present.
MODELS_DIR=""
EXTRA_ARGS=()
while [[ $# -gt 0 ]]; do
    case "$1" in
        --models-dir)
            MODELS_DIR="$2"
            shift 2
            ;;
        --models-dir=*)
            MODELS_DIR="${1#*=}"
            shift
            ;;
        *)
            # Collect remaining args for Python CLI
            EXTRA_ARGS+=("$1")
            shift
            ;;
    esac
done

if [ -z "$MODELS_DIR" ]; then
    if [ -n "${COMFY_MODELS_DIR:-}" ]; then
        MODELS_DIR="$COMFY_MODELS_DIR"
    else
        if [ -n "${COMFYUI_DIR:-}" ]; then
            SIBLING_MODELS=""
            if [ -d "$COMFYUI_DIR/../models" ]; then
                SIBLING_MODELS="$(cd "$COMFYUI_DIR/../models" && pwd)"
            fi
            if [ -n "$SIBLING_MODELS" ]; then
                MODELS_DIR="$SIBLING_MODELS"
            elif [ -d "$COMFYUI_DIR/models" ]; then
                MODELS_DIR="$COMFYUI_DIR/models"
            fi
        fi
    fi
fi

PY_ARGS=()
if [ -n "${MODELS_DIR:-}" ]; then
    PY_ARGS+=(--models-dir "$MODELS_DIR")
fi
PY_ARGS+=("${EXTRA_ARGS[@]}")

export COMFYGO_MODEL_REGISTRY_AUTORUN=0

exec uv run --python "$REPO_DIR/.venv/bin/python" \
    --no-project \
    python \
    -m custom_nodes.comfygo_model_registry.cli \
    "${PY_ARGS[@]}"
