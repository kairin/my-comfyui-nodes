# Contracts: Descriptor-First Model Registry

This directory defines the interface contracts for the model registry.

## Descriptor Schema (`comfygo-model.json`)

The canonical descriptor file uses schema `comfygo.model.v1`.

### File Location

`<model-folder>/comfygo-model.json`

### JSON Schema (informal)

```json
{
  "schema": "comfygo.model.v1",
  "name": "string — model display name",
  "kind": "string — one of: diffusers, lora, embedding, checkpoint, vae, text_encoder, controlnet, gguf, other",
  "source": {
    "type": "string — huggingface, civitai, local, or other",
    "repo": "string — source repo/URL/model ID (optional)",
    "version": "string — version ID or commit SHA (optional)"
  },
  "components": {
    "<logical-name>": {
      "path": "string — relative path to component within the package",
      "comfy_categories": ["string — ComfyUI category names"]
    }
  },
  "notes": "string (optional)",
  "workflows": ["string — relative paths to workflow files (optional)"],
  "preview_images": ["string — relative paths to preview images (optional)"],
  "documentation": ["string — relative paths to doc files (optional)"]
}
```

### Validation Rules

- `schema` MUST be exactly `"comfygo.model.v1"`
- `name` MUST be a non-empty string
- `kind` MUST be one of the recognized values
- `components` MUST be a non-empty object
- Each component `path` MUST be a relative path (no leading `/` or `../`)
- Each component `comfy_categories` MUST be a non-empty array of strings
- Unknown top-level fields are accepted (forward-compatible)
- Missing required fields → warning, descriptor skipped

## CLI Interface

The `comfygo models` subcommand exposes these operations:

### `comfygo models`

Print model root and summary.

**Exit code**: 0 (success), 1 (error)

### `comfygo models -f/--filter <name>` (or `--filter <name>`)

Print matching model folders and their category visibility.

**Exit code**: 0 (found), 1 (error or not found)

**Filter**: case-insensitive substring match against model folder names; use `-f <pattern>` or `--filter <pattern>`

### `comfygo models reconcile [-f/--filter <name>]`

Dry-run reconcile. Reports what symlinks would be created, pruned, or conflicts.

**Exit code**: 0 (success — even if changes needed), 1 (error)

**Filter**: optional — use `-f <pattern>` or `--filter <pattern>` to reconcile only matching packages

### `comfygo models reconcile [-f/--filter <name>] --apply`

Apply reconcile changes — create and prune symlinks.

**Exit code**: 0 (success), 1 (error or unresolved conflicts)

## ComfyUI Integration Contract

The `comfygo_model_registry` package integrates with ComfyUI through:

### Entry Point

`custom_nodes/comfygo_model_registry/__init__.py` — loaded automatically by
ComfyUI at startup.

### Required API

- `folder_paths.models_dir` — the configured model root directory
- `folder_paths.get_folder_paths(category)` — get list of registered paths for a category
- `folder_paths.add_model_folder_path(category, path)` — register a new path for a category

### What the registry provides

- `NODE_CLASS_MAPPINGS` dict — at minimum a no-op node (the registry's value
  is in startup behavior, not new UI nodes)
- Automatic model scanning and reconcile at module load time
