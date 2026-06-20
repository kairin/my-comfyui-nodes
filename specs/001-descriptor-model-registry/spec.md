# Feature Specification: Descriptor-First Model Registry

**Feature Branch**: `001-descriptor-model-registry`

**Created**: 2026-06-20

**Status**: Clarified after adversarial review

**Input**: User description: "Descriptor-first ComfyUI model library with automatic
compatibility views"

## Clarifications

### Session 2026-06-20

- Q: How does the CLI avoid startup side effects during dry-run? → A: The Python registry startup auto-run is gated by environment variable `COMFYGO_MODEL_REGISTRY_AUTORUN` (default "1"; set to "0" to skip). The CLI wrapper sets this to "0" before invoking `comfygo models` so that package-level `__init__.py` does not apply startup reconcile as a side effect of importing the module.
- Q: How are symlinked view directories and component-symlink escapes handled? → A: (1) `views_root()` checks whether `.comfygo_views` is itself a symlink — if so, it skips with a warning and no modifications. (2) Prune loops skip and warn on `category_dir.is_symlink()` and `model_dir.is_symlink()`. (3) Each component `target_path` is validated to be within both the package root and the model root using a resolved filesystem containment check; escaped targets are skipped with a warning.
- Q: How are `comfygo models` and auto-reconcile routed in daily operation? → A: `comfygo` and `comfygo restart` call `scripts/comfygo-models.sh` (the Python-based registry) instead of the old Bash-only model compat logic. The old shell inventory may be renamed to a debug-only internal command. This ensures LoRA, GGUF, checkpoint, and descriptor-based models work in the daily flow.
- Q: What is the idempotency reporting contract for re-reconcile? → A: On the second apply, symlinks that already point to the correct target are counted as "unchanged" (not "created"). The `views_created` list excludes entries whose correct symlink already exists.
- Q: How should tests be importable without manual PYTHONPATH? → A: Add a `pytest.ini` at the repo root with `pythonpath = .` so that `uv run pytest custom_nodes/comfygo_model_registry/tests -q` works out of the box.

### Session 2026-06-20 (Post-Implementation Review)

- Q: How does `scripts/comfygo-models.sh` resolve the models directory when called standalone? → A: The shell wrapper uses the same `models_root()` resolution as `scripts/comfy-local`: first checks explicit `--models-dir`, then `COMFY_MODELS_DIR`, then `COMFYUI_DIR` sibling models directory, then falls back to allowing Python's `folder_paths.models_dir` to resolve. The old shell precheck that exited before Python invocation was removed.
- Q: What does `comfygo models` display when no packages are detected? → A: The configured models directory path (from `--models-dir` or `folder_paths.models_dir`) is shown even when no packages are identified. `cmd_list()` accepts an explicit `models_dir` parameter and uses it as the display root when package-derived roots are empty.
- Q: How does `comfygo doctor` validate the model registry? → A: The doctor check runs `comfygo-models.sh --models-dir "$model_root" reconcile` (dry-run mode), then fails if the report contains pending creates, prunes, or conflicts. It also snapshots `.comfygo_views` before and after the dry-run with a deterministic filesystem listing and fails if the snapshot changes.
- Q: How is the AUTORUN test verified to actually prevent registry execution? → A: The test starts a fresh Python subprocess with `COMFYGO_MODEL_REGISTRY_AUTORUN=0`, injects a fake observable `folder_paths` module, imports the registry package, and asserts that neither registry registration nor reconcile side effects occurred.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Descriptor-Based Model Detection (Priority: P1)

A user downloads a Hugging Face Diffusers model package into
`$COMFYUI_MODELS_DIR/Qwen-Image-Edit-2511-4bit`.
The model folder contains `model_index.json`, `transformer/`, `text_encoder/`, and
`vae/`. The system detects it as a self-identifying package, infers its components,
and creates compatibility symlinks under `.comfygo_views/`. After restarting
ComfyUI, existing nodes that browse `diffusion_models`, `text_encoders`, or `vae`
can see the model components without any per-node changes.

**Why this priority**: This is the core value proposition — users install models
once in their own folder, and everything just works in ComfyUI without manual
category placement.

**Independent Test**: A Diffusers-style folder with `model_index.json` and known
subdirectories (`transformer/`, `text_encoder/`, `vae/`) is placed under the model
root. After running `comfygo models reconcile --apply`, symlinks appear under
`.comfygo_views/` mapping each subdirectory to its ComfyUI category. Restarting
ComfyUI makes those model files selectable from standard node dropdowns.

**Acceptance Scenarios**:

1. **Given** a Diffusers model folder `Qwen-Image-Edit-2511-4bit` with
   `model_index.json`, `transformer/`, `text_encoder/`, `vae/` under the model
   root, **When** the system scans the model root, **Then** it detects the folder
   as a self-identifying package and infers components with default category
   mappings.
2. **Given** a folder `My-LoRA` with only a `.safetensors` file and no descriptor,
   **When** the system scans, **Then** it does not create any compatibility views
   for that folder (ambiguous single file).
3. **Given** a folder `Stable-Diffusion-v1-5` with `comfygo-model.json` that
   explicitly maps components to categories, **When** the system scans, **Then** it
   uses the descriptor as the primary source of truth even if other inference rules
   would produce different results.

---

### User Story 2 - CLI Model Management (Priority: P2)

A user wants to inspect what models are known and whether they are visible to
ComfyUI categories. They run `comfygo models` to see the model root and summary.
They run `comfygo models -f Qwen-Image-Edit-2511-4bit` to see where that model
lives and which categories can see its components. They run `comfygo models
reconcile` to dry-run what symlinks would be created, then `comfygo models
reconcile --apply` to create them.

**Why this priority**: The CLI gives users visibility and control over the
registry without requiring ComfyUI to be running. It also provides the safe
dry-run-before-apply workflow demanded by the constitution.

**Independent Test**: Running `comfygo models` without arguments prints the model
root path and a summary of known packages. Running `comfygo models
-f <partial-name>` prints matching folders and their category visibility.
Running `comfygo models reconcile` shows what would change without creating
files. Running `comfygo models reconcile --apply` creates the symlinks.

**Acceptance Scenarios**:

1. **Given** a model root with detected packages, **When** running
   `comfygo models`, **Then** the output includes the model root path, count of
   identified packages, and count of ambiguous folders.
2. **Given** a known package `Qwen-Image-Edit-2511-4bit`, **When** running
   `comfygo models -f Qwen-Image-Edit-2511-4bit`, **Then** the output shows
   the canonical folder path and which ComfyUI categories can see each
   component.
3. **Given** no compatibility views exist yet, **When** running `comfygo models
   reconcile --apply`, **Then** symlinks are created under `.comfygo_views/` for
   each inferred or declared component mapping.

---

### User Story 3 - Automatic Reconcile On Launch (Priority: P2)

A user runs `comfygo start` or `comfygo restart`. Before launching ComfyUI, the
system automatically reconciles identifiable model packages so that startup
nodes see the current state of the model library.

**Why this priority**: Users should not need to remember a separate reconcile
step. Normal daily operation (`comfygo`) should keep the model library in sync
automatically without risking destructive operations.

**Independent Test**: Add a new Diffusers folder under the model root. Run
`comfygo start`. Before ComfyUI launches, the system creates compatibility
views. After launch, the model is visible in ComfyUI node dropdowns. Remove the
folder, run `comfygo start` again — stale symlinks are cleaned up.

**Acceptance Scenarios**:

1. **Given** a new identifiable model package placed under the model root,
   **When** running `comfygo` or `comfygo start`, **Then** `.comfygo_views/` is
   updated before ComfyUI launches.
2. **Given** a previously reconciled model package that has been removed from
   the model root, **When** running `comfygo` or `comfygo start`, **Then** stale
   symlinks for that package are removed from `.comfygo_views/`.
3. **Given** a model root with no identifiable packages, **When** running
   `comfygo start`, **Then** no `.comfygo_views/` changes are made and ComfyUI
   launches normally.

---

### User Story 4 - Migration Support And Backward Compatibility (Priority: P3)

A user has existing model files in legacy category folders such as
`$COMFYUI_MODELS_DIR/diffusers/some-model`. The system does not move or delete
those files. New downloads may be placed directly under
`$COMFYUI_MODELS_DIR/<model-folder>`. Category folders remain accessible during
transition. A future migration command may propose moving category contents into
canonical folders, but only with explicit non-destructive dry-run-first behavior.

**Why this priority**: Existing users have working setups that must not break.
Backward compatibility is essential, but the new canonical folder layout is the
long-term source of truth.

**Independent Test**: A model in `$COMFYUI_MODELS_DIR/diffusers/some-model`
with `model_index.json` is scanned. It is detected and receives compatibility
views. The original `diffusers/` folder is not removed or modified. After
reconcile, both the legacy path and the new `.comfygo_views/` approach produce
equivalent ComfyUI visibility.

**Acceptance Scenarios**:

1. **Given** a Diffusers package under the legacy `diffusers/` category folder,
   **When** the system scans, **Then** it is detected and compatibility views
   are created without moving or copying the original files.
2. **Given** a legacy category folder with manually placed files, **When** the
   system scans, **Then** the category folder itself is skipped (it is a
   reserved ComfyUI category folder) and its contents are not touched.
3. **Given** a transition period with both canonical and category folders,
   **When** running reconciliation, **Then** no automatic deletion or migration
   occurs — only symlinks are created.

---

### Edge Cases

- What happens when a `comfygo-model.json` references a component path that does
  not exist on disk? The system MUST report a warning and skip that component
  rather than creating a broken symlink.
- What happens when two canonical folders produce a symlink conflict
  (same model name in the same category)? The system MUST report the conflict
  and not overwrite — require user resolution.
- What happens when a Diffusers package has only `model_index.json` but no
  expected subdirectories? The system MUST detect the package as
  self-identifying but report each missing expected component.
- What happens when the model disk is full or read-only? The system MUST
  report the reconcile error and warn that compatibility views may be unusable.
  If reconcile is running as a pre-launch step, the launcher MAY stop before
  starting ComfyUI; import-time registry code MUST NOT claim it can stop an
  already-running server.
- What happens when `.comfygo_views` already contains stale symlinks for a
  previously deleted package? Reconcile MUST prune stale entries.
- What happens when a model folder contains an empty `comfygo-model.json` or
  one with an unrecognized schema version? The system MUST report a warning
  and skip the descriptor.
- What happens when `.comfygo_views` is itself a symlink? The system MUST skip
  all view operations and warn — do not follow symlinks for the views root.
- What happens when a component's folder is a symlink to a path outside the
  model root? The system MUST detect the escape, skip the component, and
  report a warning.
- What happens when a side-effect-free CLI invocation (`comfygo models`)
  triggers startup-style reconcile? The Python module MUST gate startup
  reconcile behind `COMFYGO_MODEL_REGISTRY_AUTORUN` (set to "0" for CLI use),
  preventing import-time side effects.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST detect self-identifying model packages by scanning
  top-level folders under the configured model root, the optional
  `models/library/*` path, and the optional legacy `models/diffusers/*` path.
- **FR-002**: The system MUST use `comfygo-model.json` (schema `comfygo.model.v1`)
  as the primary descriptor when present in a model folder. Components and
  category mappings from the descriptor MUST take precedence over inference.
- **FR-003**: The system MUST infer components from `model_index.json` for
  Diffusers-style packages. Default inference: `transformer/` → `diffusion_models`,
  `text_encoder/` → `text_encoders`, `vae/` → `vae`.
- **FR-004**: The system MUST NOT create compatibility views for folders that
  contain only a single `.safetensors` file or other ambiguous single files
  without a descriptor.
- **FR-005**: The system MUST generate compatibility views as symlinks only,
  under `.comfygo_views/<category>/<model-name>/<component-name>`. No model
  files may be copied or moved. The `.comfygo_views` root MUST be checked for
  being a symlink before any operations — if it is a symlink, reconcile MUST
  skip with a warning. Prune loops MUST skip and warn on symlinked category
  and model directories.
- **FR-006**: The system MUST register generated view paths with ComfyUI's
  `folder_paths.add_model_folder_path` at startup so that existing nodes using
  `folder_paths.get_filename_list(...)` can see compatible entries.
- **FR-007**: The system MUST provide CLI subcommands: `comfygo models`
  (summary), `comfygo models -f/--filter <name>` (filtered listing),
  `comfygo models reconcile [-f/--filter <name>]` (dry-run), and
  `comfygo models reconcile [-f/--filter <name>] --apply` (apply changes).
  The CLI MUST use `-f/--filter` for filtering (not a positional argument) to
  avoid argparse conflicts with subcommands.
- **FR-008**: `comfygo models reconcile` MUST be dry-run by default — no files
  are created, modified, or deleted without `--apply`. The Python registry
  module MUST gate startup-style reconciliation behind environment variable
  `COMFYGO_MODEL_REGISTRY_AUTORUN` (default "1"). The CLI shell wrapper MUST
  set `COMFYGO_MODEL_REGISTRY_AUTORUN=0` before invoking the Python module
  for `comfygo models` commands to prevent import-time side effects.
- **FR-009**: The system MUST be idempotent — re-running `reconcile --apply`
  with no state changes MUST produce the same result without errors. Existing
  correct symlinks MUST be reported as "unchanged" (not "created") on
  subsequent runs.
- **FR-010**: The system MUST skip reserved ComfyUI category folder names
  (e.g., `diffusion_models`, `text_encoders`, `vae`, `loras`, `embeddings`,
  `controlnet`, `checkpoints`) and hidden folders (dot-prefixed) except
  `.comfygo_views`.
- **FR-011**: The vendored custom node extension MUST be named
  `comfygo_model_registry` and run at ComfyUI startup.
- **FR-012**: `comfygo`, `comfygo start`, and `comfygo restart` MUST
  automatically reconcile identifiable model packages before launching ComfyUI.
  The auto-reconcile MUST route through the Python registry
  (`custom_nodes/comfygo_model_registry`), not through legacy shell logic.
- **FR-013**: Symlinks generated by the system MUST stay inside the configured
  model root — no symlinks may escape `.comfygo_views/`. Each component's
  target path MUST be validated during both dry-run and apply reconciliation to
  be within both its package root and the model root using a resolved
  filesystem containment check. Component folders that are themselves symlinks
  to paths outside the model root MUST be detected, skipped, and reported as a
  warning.
- **FR-014**: The system MUST prune stale symlinks from `.comfygo_views/` when
  a model folder has been removed or no longer produces the same component
  mapping.
- **FR-015**: The system MUST report conflicts (e.g., two model folders with
  the same name mapping to the same category) and skip the conflicting entry
  rather than silently overwriting.
- **FR-016**: Tests MUST cover descriptor parsing (including path-traversal
  rejection), Diffusers inference, reserved-folder skipping, symlink
  generation, idempotency, conflict handling, ambiguous-folder rejection,
  CLI argument parsing and filter matching, path traversal and symlink-escape
  rejection, view-directory symlink safety, and importability with documented
  commands.

### Repository Policy Requirements

- Features that invoke Python or comfy-cli commands MUST use uv-first command
  forms: `uv run`, `uv pip --python <workspace-python>`, or
  `uv run --python <workspace-python> --no-project python ...`.
- Features MUST NOT introduce direct `pip`, `python -m pip`, or unwrapped
  `python` workflow commands. If `uv` is missing, the feature must stop with an
  instruction to install `uv` first.
- No tokens, model files, generated views, caches, logs, user prompts, or local
  runtime state may be committed to this repo.
- Code and configuration files that reference model root paths MUST use
  configurable variables or environment variables (e.g., `folder_paths.models_dir`),
  not hard-coded absolute paths, to keep the repo public-safe.

### Key Entities *(include if feature involves data)*

- **Model Package**: A folder under the model root that is self-identifying as a
  model. Self-identification comes from either (a) a `comfygo-model.json`
  descriptor, or (b) a `model_index.json` (Diffusers-style). Each package has
  a name derived from its folder name, a kind (diffusers, lora, embedding,
  checkpoint, vae, text_encoder, controlnet, gguf, other), source metadata, and
  one or more components.
- **Component**: A subdirectory or file within a model package that maps to a
  ComfyUI category. Each component has a relative path within the package, a
  logical name (e.g., `transformer`), and a list of target ComfyUI categories
  (e.g., `diffusion_models`). The mapping between components and categories is
  declared in `comfygo-model.json` or inferred for Diffusers packages.
- **Compatibility View**: A generated symlink under
  `.comfygo_views/<category>/<model-name>/<component-logical-name>` pointing to
  the real component path. Compatibility views are disposable — they can be
  regenerated from descriptors at any time.
- **Descriptor (`comfygo-model.json`)**: A JSON file using schema
  `comfygo.model.v1` that declares the model name, kind, source, components,
  and optional metadata (notes, workflows, preview images, documentation links).
  This is the authorative declaration of a model package's structure.
- **Ambiguous Folder**: A folder under the model root that is not
  self-identifying (no descriptor, no `model_index.json`, no recognized
  structure). Ambiguous folders are ignored until a descriptor is added or the
  user confirms the model structure explicitly.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A Diffusers-style folder (`model_index.json` + `transformer/` +
  `text_encoder/` + `vae/`) placed under the model root is detected and
  receives compatibility symlinks within one reconcile pass, with no user
  configuration required.
- **SC-002**: Running `comfygo models -f Qwen-Image-Edit-2511-4bit` reports the
  canonical folder path and which ComfyUI categories can see each component.
  Running `comfygo models` (no filter) prints model root(s), identified count,
  and ambiguous count.
- **SC-003**: `comfygo models reconcile` (dry-run) produces a report of what
  would be created and removed without modifying the filesystem.
- **SC-004**: `comfygo models reconcile --apply` creates only symlinks — zero
  model files are copied, moved, or deleted.
- **SC-005**: After `comfygo restart`, ComfyUI nodes that browse
  `diffusion_models`, `text_encoders`, or `vae` categories can select the
  relevant model components without any node-specific code changes.
- **SC-006**: Existing manually placed model files in legacy category folders
  are not moved, copied, or deleted by any reconcile or startup operation.
- **SC-007**: `comfygo doctor` passes with the model registry enabled only when
  all registry-health checks pass: the source registry package exists in this
  repo, the runtime `custom_nodes/comfygo_model_registry` copy is present after
  sync, the configured model root is readable, `uv` is available, the CLI
  wrapper can run the documented dry-run command successfully, the dry-run
  reports no pending creates, prunes, or conflicts, and a deterministic
  before/after snapshot proves that `.comfygo_views` was not created, removed,
  or altered. The documented dry-run command is
  `scripts/comfygo-models.sh --models-dir "$model_root" reconcile`.
- **SC-008**: Test suite covers descriptor parsing, Diffusers inference,
  reserved-folder skipping, symlink generation, idempotency, conflict
  handling, and ambiguous-folder rejection. All tests pass.

## Assumptions

- The model root defaults to ComfyUI's `folder_paths.models_dir`. The specific
  path is configured by the user's local environment and is not hard-coded in
  this repo.
- `uv` is available in the execution environment. If not, operations fail with
  an installation instruction.
- The ComfyUI `folder_paths` module is available at runtime via the vendored
  custom node's execution context.
- Existing category folders (`diffusion_models/`, `text_encoders/`, `vae/`,
  etc.) remain in place during the migration period and are not modified by
  registry operations.
- Users have write permission to `.comfygo_views/` under the model root. If
  the filesystem is read-only, reconcile reports the error.
- The system targets Linux (the ComfyUI deployment environment). Symlink
  generation assumes POSIX symlink semantics.
- Generated `.comfygo_views/` directories may be removed and recreated at any
  time — they are disposable.
- The `comfygo_model_registry` custom node is vendored under
  `custom_nodes/comfygo_model_registry/` as per the project's operational
  constraints.
