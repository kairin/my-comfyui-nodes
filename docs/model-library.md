# Model Library

This document describes the descriptor-first model library system managed by
the `comfygo_model_registry` custom node and the `comfygo models` CLI.

## Canonical Model Layout

Instead of manually placing model files into ComfyUI category folders, each
model lives in its own folder under the model root:

```
$COMFYUI_MODELS_DIR/
├── My-Diffusers-Model/
│   ├── model_index.json
│   ├── transformer/
│   ├── text_encoder/
│   ├── vae/
│   ├── README.md
│   └── sample.png
├── My-LoRA/
│   ├── comfygo-model.json       ← descriptor (optional but recommended)
│   └── my-lora.safetensors
├── Example-Model-Package/
│   ├── comfygo-model.json
│   ├── transformer/
│   └── ...
└── .comfygo_views/              ← auto-generated (do not edit)
    ├── diffusion_models/
    │   └── My-Diffusers-Model/transformer → ../../My-Diffusers-Model/transformer
    ├── text_encoders/
    │   └── My-Diffusers-Model/text_encoder → ../../My-Diffusers-Model/text_encoder
    └── vae/
        └── My-Diffusers-Model/vae → ../../My-Diffusers-Model/vae
```

## How It Works

1. **Place** a model folder under `$COMFYUI_MODELS_DIR/` with either:
   - A `comfygo-model.json` descriptor (for any model type)
   - A `model_index.json` (for Diffusers packages — inferred automatically)
2. **Run** `comfygo models reconcile --apply` to generate compatibility views.
3. **Launch** ComfyUI — existing nodes can browse model files from the standard
   category dropdowns.

For new downloads, use the included helper so files arrive in that canonical
folder with metadata:

```bash
scripts/hf-select-download https://huggingface.co/owner/example-model \
  --package-name Example-Model-Package \
  --models-root $COMFYUI_MODELS_DIR
```

This helper:

- Shows available files and lets you choose which ones to download.
- Shows local state per file when a package folder is targeted (`complete`, `partial`, or `missing`).
- Verifies each selected file with `hf download ... --dry-run`.
- Downloads files with resumable `curl` into `$COMFYUI_MODELS_DIR/Example-Model-Package/`.
- Writes `comfygo-model.json` metadata in the package folder for registry-aware
  discovery.
- Writes `.comfygo-download.json` with download provenance (repo, revision,
  selected files, timestamp).
- Use `--category-mapping "mmproj*.gguf:text_encoders"` if you need to force a
  specific category mapping.
- Use `--only-missing` to hide already-complete files and download only remaining
  files in an existing package folder.

To resume from an existing package folder after moving/renaming it, use:

```bash
scripts/hf-select-download \
  --resume-from /path/to/renamed/package/folder
```

The helper reads `.comfygo-download.json` (or `comfygo-model.json`) in that folder
to recover the original Hugging Face repo, then lists the same remote file set and
lets you pull anything still missing.

If you only know the Hugging Face URL and no metadata exists yet, you can run from
the folder directly. If metadata is missing, the helper will prompt for a URL:

```bash
cd $COMFYUI_MODELS_DIR/example-model
scripts/hf-select-download .
```

When prompted, paste:

`https://huggingface.co/owner/example-model`

Pressing **Enter** on the prompt without input leaves the command in a safe no-op mode.

That stores the source metadata in `.comfygo-download.json` so future runs can be
started with only:

```bash
scripts/hf-select-download .
```

On each `comfygo`/`comfygo start`/`comfygo restart`, the registry
automatically reconciles identifiable packages before ComfyUI starts.

## Descriptor Schema (`comfygo-model.json`)

For models that don't use the Diffusers folder structure (or when you want
explicit control), create a `comfygo-model.json` file in your model folder:

```json
{
  "schema": "comfygo.model.v1",
  "name": "Example-Diffusers-Model",
  "kind": "diffusers",
  "source": {
    "type": "huggingface",
    "repo": "owner/repo"
  },
  "components": {
    "diffusion_model": {
      "path": "transformer",
      "comfy_categories": ["diffusion_models"]
    },
    "text_encoder": {
      "path": "text_encoder",
      "comfy_categories": ["text_encoders"]
    },
    "vae": {
      "path": "vae",
      "comfy_categories": ["vae"]
    }
  }
}
```

### Fields

| Field | Required | Description |
|-------|----------|-------------|
| `schema` | Yes | Must be `"comfygo.model.v1"` |
| `name` | Yes | Display name for the model |
| `kind` | Yes | One of: `diffusers`, `lora`, `embedding`, `checkpoint`, `vae`, `text_encoder`, `controlnet`, `gguf`, `other` |
| `source` | No | Origin metadata (`type`, `repo`, `version`) |
| `components` | Yes | Object mapping component names to their paths and category targets |
| `notes` | No | Free-text notes |
| `workflows` | No | List of workflow file paths |
| `preview_images` | No | List of preview image file paths |
| `documentation` | No | List of documentation file paths |

## CLI Commands

### `comfygo models`

Show the model root path and a summary of known packages:

```text
Model root(s): $COMFYUI_MODELS_DIR
Identified packages: 3
Ambiguous folders: 1
```

### `comfygo models -f/--filter <name>`

Show matching model folders and their category visibility. Filter is a
case-insensitive substring match:

```text
Matching "Example":
  Example-Diffusers-Model  canonical:
    diffusion_model → diffusion_models
    text_encoder → text_encoders
    vae → vae
```

### `comfygo models reconcile [-f/--filter <name>]`

Dry-run reconcile. Reports what symlinks would be created or pruned without
making changes:

```text
Dry-run reconcile:
  Created: $COMFYUI_MODELS_DIR/.comfygo_views/diffusion_models/...
  Created: $COMFYUI_MODELS_DIR/.comfygo_views/text_encoders/...
```

### `comfygo models reconcile [-f/--filter <name>] --apply`

Apply reconcile — creates symlinks and prunes stale entries:

```text
Reconcile complete: 3 view(s) created; 0 stale view(s) pruned
```

## Automatic Reconcile

`comfygo`, `comfygo start`, and `comfygo restart` automatically reconcile
identifiable model packages before launching ComfyUI. This means you don't
need to remember a separate reconcile step — just add a model folder and
run `comfygo`.

## Registry Health

`comfygo doctor` should treat the model registry as healthy only when:

- `custom_nodes/comfygo_model_registry/` exists in this repo.
- The synced runtime copy exists under ComfyUI's `custom_nodes/`.
- The configured model root is readable.
- `uv` is installed and available.
- `scripts/comfygo-models.sh --models-dir "$MODEL_ROOT" reconcile` completes
  in dry-run mode with no pending creates, prunes, or conflicts.
- A deterministic before/after snapshot confirms the dry-run did not create,
  remove, or alter `.comfygo_views/`.

Pending registry changes are not considered healthy by default. Run the dry-run
to inspect the proposed changes, then apply them explicitly:

```bash
scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile
scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile --apply
```

## Migration From Category Folders

If you have existing model files in legacy category folders
(`diffusion_models/`, `text_encoders/`, `vae/`, etc.), they continue to work
unmodified. No files are moved, copied, or deleted automatically.

To adopt the canonical layout, move models into their own folders and add
descriptors as needed. A future migration command may automate this with
a safe dry-run-first workflow.

## Troubleshooting

**Model not showing up in ComfyUI:**
1. Run `comfygo models -f <name>` to check if the model is detected.
2. Run `comfygo models reconcile --apply` to generate views.
3. Restart ComfyUI so the new views are registered.
4. If still not visible, check that the component paths in your descriptor
   actually exist.

**"Ambiguous folder" warning:**
The folder doesn't have a `comfygo-model.json` or `model_index.json` and
can't be inferred. Add a descriptor or confirm the model type explicitly.

**Symlink conflict warning:**
Two model folders result in the same symlink target. Rename one of the
folders to resolve the conflict.
