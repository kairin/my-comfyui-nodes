# Research: Descriptor-First Model Registry

**Phase 0 output** — Technical research and design decisions.

## Key Decisions

### ComfyUI Custom Node Structure

**Decision**: Follow ComfyUI standard custom node pattern: `__init__.py` in a
package directory under `custom_nodes/`. The package is auto-discovered by
ComfyUI at startup.

**Rationale**: This is the universal ComfyUI custom node convention.
No `node_map.cfg` or additional registration files needed.

**References**:
- ComfyUI scans `custom_nodes/` for directories with `__init__.py`
- Nodes register via `NODE_CLASS_MAPPINGS` and `NODE_DISPLAY_NAME_MAPPINGS`
- The `folder_paths` module is available at import time and provides
  `add_model_folder_path()` and `get_filename_list()`

### ComfyUI `folder_paths` API

**Decision**: Use `folder_paths.add_model_folder_path(category, path)` to
register generated `.comfygo_views/<category>/` paths. This makes model
components visible to existing ComfyUI nodes that call
`folder_paths.get_filename_list(category)`.

**Rationale**: `folder_paths.add_model_folder_path` is ComfyUI's public API
for extending model directory visibility. It appends a path to the internal
list for a given category, and `get_filename_list` merges all registered paths
when building file lists for node dropdowns. No per-node changes needed.

**Alternatives considered**:
- Creating symlinks directly into ComfyUI's category folders is also supported
  by the codebase, but `add_model_folder_path` gives more control and avoids
  cluttering the canonical ComfyUI folder structure.

### Symlink-Only Compatibility Views

**Decision**: `comfygo_model_registry` creates symlinks only. No file copying,
no hard links, no bind mounts.

**Rationale**: Symlinks are zero-copy, survive ComfyUI restart, can be pruned
atomically, and are POSIX-standard on Linux. They allow the canonical model
folder to remain the single source of truth while providing category-based
visibility.

**Edge cases**:
- Broken symlinks: skipped or removed during reconcile
- Symlink conflicts (same model name in same category): reported, not overwritten
- Cross-filesystem symlinks: resolved if on the same filesystem; on some Docker
  or NFS setups, symlinks may not span mount points — documented limitation

### CLI Integration

**Decision**: Implement `comfygo models` as a shell script wrapper
(`scripts/comfygo-models.sh`) that delegates to the Python package.
This follows the existing `comfygo` wrapper pattern in this repo.

**Rationale**: The existing comfygo CLI is shell-script based. Adding the
`models` subcommand as a shell wrapper that calls `uv run` is the most
consistent integration path. The Python module handles all the actual scanning
and reconcile logic.

**Subcommand structure**:
- `comfygo models` → show root + summary
- `comfygo models -f/--filter <name>` → show matching models and their visibility
- `comfygo models reconcile -f/--filter <name>` → dry-run for matching packages
- `comfygo models reconcile -f/--filter <name> --apply` → create symlinks for matching packages

### Descriptor Schema (`comfygo.model.v1`)

**Decision**: The `comfygo-model.json` descriptor follows the schema specified
in the feature spec. Validation is strict: unknown fields are accepted
(forward-compatible), missing required fields produce a warning and the
descriptor is skipped.

**Rationale**: Strict validation prevents silent misconfiguration. Forward
compatibility on unknown fields allows schema evolution without breaking
existing descriptors.

## ComfyUI Path Registration Flow

```
ComfyUI startup
  → custom_nodes/comfygo_model_registry/__init__.py imported
  → scanner.scan_models(models_dir)
    → for each top-level folder:
      → skip if reserved category folder name
      → skip if hidden folder (except .comfygo_views)
      → check for comfygo-model.json → use descriptor (skip remaining checks)
      → check for model_index.json → infer Diffusers components
      → otherwise → mark ambiguous, skip
  → reconciler.reconcile(identified_packages, models_dir)
    → dry-run mode: report what would be created/removed
    → apply mode: create symlinks under .comfygo_views/, prune stale ones
  → for each category with generated views:
    → folder_paths.add_model_folder_path(category, .comfygo_views/<category>/)
```

## Test Strategy

- **Unit tests** (stdlib `unittest` or `pytest`):
  - Descriptor parsing: valid schema, missing fields, bad JSON, unknown fields
  - Diffusers inference: `model_index.json` with/without expected subdirs
  - Reserved folder skipping: known category names, hidden folders
  - Symlink generation: verify correct paths and target resolution
  - Idempotency: re-running reconcile produces same state
  - Conflict handling: same name, same category → reported, not overwritten
  - Ambiguous folder rejection: single safetensors, single other file, empty dir
- **Integration tests** (via `uv run pytest` in a temp directory):
  - Full scan → reconcile → verify symlinks created
  - Scan + reconcile + add folder + scan + reconcile → verify new symlinks
  - Scan + reconcile + remove folder + scan + reconcile → verify stale symlinks
  - Cleanup: verify .comfygo_views/ can be fully regenerated

## Alternatives Considered And Rejected

| Alternative | Why Rejected |
|-------------|--------------|
| Patch `folder_paths` source code | Would break on ComfyUI updates; violates Patch Durability principle |
| Use ComfyUI's `extra_model_paths.yaml` | Static, no inference support, must be manually maintained |
| Copy model files into category folders | Destructive duplication; violates no-copy constraint |
| Python-only CLI (click/typer) | Adding external `pip` dependency violates uv-first for code in this repo; argparse is stdlib |
| Scan on every ComfyUI file-list request | Too expensive; once at startup is sufficient and safe |
