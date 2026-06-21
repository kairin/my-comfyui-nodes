# Feature Specification: Model Garbage Collection (comfygo models gc)

**Feature Branch**: `002-model-gc`

**Created**: 2026-06-20

**Status**: Clarified after adversarial review

**Input**: User description: "Safe garbage collection for model folders with
dry-run, quarantine, and marker-based ownership proof"

## Clarifications

### Session 2026-06-21

- Q: How should GC reuse existing scanner behavior while preserving symlink-safe raw folder discovery? → A: GC performs its own raw top-level directory scan; it may reuse scanner reserved-folder policy only, and CLI dispatch passes models_dir/filter/apply directly without scanner packages.
- Q: How should example model-root paths be written for public repo safety? → A: Use `$COMFYUI_MODELS_DIR` or `<model-root>` placeholders, never machine-local absolute paths.
- Q: How should empty GC report sections be printed? → A: Omit empty sections; if no entries remain after filtering, print exactly `Nothing to report.`
- Q: What exit behavior applies when GC sees a source symlink? → A: Unfiltered dry-run exits 0 with a warning; filtered dry-run or apply targeting only source symlinks exits 1 with the refusal warning.
- Q: How should the plan's GC scan performance target be verified? → A: Add a perf smoke task for ~100 temp folders and require dry-run scan completion under 1 second.
- Q: Should unsafe or long managed folder names be resolved by GC or by a separate normalization/install behavior? → A: Use a separate normalization/install behavior: downloaded managed folders may be moved into the model root as short safe names like `<kind>-NNN`, with JSON metadata preserving identity; GC remains quarantine-only.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - View-Side Stale Pruning (Priority: P1)

A user has removed a model folder from the model root. The stale compatibi‑
lity symlinks under `.comfygo_views/` left behind after the last reconcile
are no longer useful. The user runs `comfygo models reconcile --apply` and
the stale views are pruned. This is the existing feature — maintenance of
this behavior under the gc umbrella.

**Why this priority**: Without this, removed models leave orphaned views in
ComfyUI dropdowns. Already implemented in feature 001.

### User Story 2 - GC Dry-Run Inspection (Priority: P1)

A user wants to see which folders under the model root are managed by
comfygo (have marker files) and which are ambiguous. They run
`comfygo models gc` to see a report without modifying anything.

The output is a dry-run report (exact format per contracts):

```
Managed folders:
  $COMFYUI_MODELS_DIR/Old-Qwen-Test
    marker: downloader
  $COMFYUI_MODELS_DIR/abandoned-experiment
    marker: descriptor

Ambiguous:
  $COMFYUI_MODELS_DIR/LLM
  $COMFYUI_MODELS_DIR/audio_encoders

Warnings:
  (only shown when warning entries exist)
```

Full contract: "Managed folders" lists folders with markers (with "marker: " line), "Ambiguous" for no marker, "Warnings" for issues. See contracts/README.md for exact strings and exit codes.
Empty report sections are omitted. If no managed, ambiguous, or warning
entries remain after filtering, GC prints exactly `Nothing to report.`

**Why this priority**: Users must be able to preview what GC sees before
deciding what to quarantine. Dry-run is the default — safe by design.

**Independent Test**: Place a folder with `.comfygo-download.json` under the
model root. Run `comfygo models gc`. Output lists the folder under
"Managed folders" but no files are moved. No `.comfygo_trash/` directory
is created.

**Acceptance Scenarios**:

1. **Given** a model root with one or more folders containing a
   `.comfygo-download.json` or `comfygo-model.json` marker file,
   **When** running `comfygo models gc`, **Then** a dry-run report lists
   each such folder under "Managed folders".
2. **Given** a model root with folders that contain no marker file,
   **When** running `comfygo models gc`, **Then** those folders are listed
   under "Ambiguous" and are never moved.
3. **Given** an empty model root, **When** running `comfygo models gc`,
   **Then** the output says nothing to report and exits 0.
4. **Given** a managed folder with an empty or unparseable marker file,
   **When** running `comfygo models gc`, **Then** the folder is listed
   under "Managed folders" with a warning about the unparseable marker.

---

### User Story 3 - GC Apply With Explicit Target (Priority: P2)

After inspecting the dry-run report, the user decides to quarantine a
specific managed folder. They run
`comfygo models gc -f Old-Qwen-Test --apply`.

The system moves the folder to a dated subdirectory under
`.comfygo_trash/`:

```
$COMFYUI_MODELS_DIR/.comfygo_trash/2026-06-20/Old-Qwen-Test/
```

After quarantine, the old path under `$COMFYUI_MODELS_DIR/` no longer
exists. The user can restore the folder by moving it back manually.

GC requires an explicit `-f NAME` flag for any destructive action. The
filter must resolve to exactly one managed folder. If zero, ambiguous-only,
or multiple managed folders match, GC reports the situation and performs
no mutation.

Exact error messages (per contracts):
- `--apply` without `-f`: "error: --apply requires -f NAME"
- no managed match: "No managed folder matching 'NAME'"
- ambiguous-only: "Folder 'NAME' is not managed by comfygo"
- multiple: "Filter 'NAME' matched multiple managed folders" (then list)
- source symlink: "warning: Refusing to quarantine symlinked folder '<path>'"
- cross-fs: "error: Cannot quarantine across filesystems; no files changed"
- unsafe source folder name: "error: Unsafe path segment: '<name>'; no files changed"

**Why this priority**: Quarantine is safer than deletion — it preserves the
data while removing it from ComfyUI's view. The date-prefixed trash
structure supports bulk recovery. The unique-match requirement prevents
accidental quarantine of the wrong folder.

**Independent Test**: Run `comfygo models gc` (dry-run) first, confirm
output lists the target folder. Then run
`comfygo models gc -f Old-Qwen-Test --apply`. Verify:
(1) the marked folder is moved to `.comfygo_trash/YYYY-MM-DD/name/`,
(2) the original path no longer exists under the model root,
(3) no files are deleted or altered — only relocated.

**Acceptance Scenarios**:

1. **Given** a folder with `.comfygo-download.json` under the model root,
   **When** running `comfygo models gc -f <folder> --apply`,
   **Then** that folder is moved to `.comfygo_trash/<date>/<name>/` and
   removed from the model root. Other managed folders are not touched.
2. **Given** a folder with `comfygo-model.json` under the model root,
   **When** running `comfygo models gc -f <folder> --apply`,
   **Then** that folder is quarantined identically to a downloader-marked
   folder.
3. **Given** the `.comfygo_trash/` directory does not exist,
   **When** running `comfygo models gc -f <folder> --apply`,
   **Then** it is created automatically.
4. **Given** a folder name that matches no managed folder,
   **When** running `comfygo models gc -f Nonexistent --apply`,
   **Then** GC exits 1.
5. **Given** an ambiguous folder name (no marker),
   **When** running `comfygo models gc -f <ambiguous> --apply`,
   **Then** GC exits 1.
6. **Given** a filter that matches two or more managed folders,
   **When** running `comfygo models gc -f partial --apply`,
   **Then** GC reports the matches and exits 1, moving no folders.

---

### User Story 4 - Ambiguous Folder Reporting (Priority: P2)

A user has folders under the model root that were placed there manually
with no marker file. These folders are not owned by comfygo. The GC
reports them as ambiguous and takes no action, even with `--apply`.

**Why this priority**: Users need to understand why a folder was not
eligible. Explicit "ambiguous" output prevents confusion and accidental
data loss.

**Independent Test**: Create a folder with no `.comfygo-download.json` or
`comfygo-model.json` under the model root. Run `comfygo models gc`. The
output lists the folder under "Ambiguous".

**Acceptance Scenarios**:

1. **Given** a folder under the model root with no marker file,
   **When** running `comfygo models gc`, **Then** it is reported as
   ambiguous.
2. **Given** a folder that is a reserved ComfyUI category name
   (e.g., `diffusion_models/`, `vae/`), **When** running `comfygo models
   gc`, **Then** it is skipped silently and not listed as ambiguous.
3. **Given** a hidden folder (dot-prefixed, e.g., `.comfygo_trash/`,
   `.comfygo_views/`), **When** running `comfygo models gc`,
   **Then** it is skipped silently.
4. **Given** a source entry that is a symlink to a directory,
   **When** running `comfygo models gc`, **Then** it is skipped with
   warning "Refusing to quarantine symlinked folder '<path>'" and never
   quarantined.

---

### Edge Cases

- **Empty marker file**: A folder with an empty or unparseable
  `.comfygo-download.json` is still treated as managed (the marker file
  itself is the ownership proof). GC reports it under Managed folders but
  adds a warning about the unparseable metadata. It can still be
  quarantined with `-f NAME --apply`.
- **Cross-filesystem quarantine**: If `.comfygo_trash/` would be on a
  different filesystem from the model root, GC reports the error and
  does not move the folder. No copy+delete fallback.
- **Destination collision**: If `.comfygo_trash/<date>/<name>/` already
  exists, GC appends a numeric suffix (`<name>-1`, `<name>-2`) and
  warns. Never overwrites. Also treats symlinks at the destination as
  collisions.
- **Symlinked `.comfygo_trash`**: If `.comfygo_trash` is itself a
  symlink, GC refuses to operate and reports a warning. Same for
  symlinked date subdirectories.
- **Source folder is a symlink**: GC refuses to quarantine a folder
  whose top-level entry is a symlink. Unfiltered dry-run reports
  `warning: Refusing to quarantine symlinked folder '<path>'` and exits 0
  without mutation. Filtered dry-run or `-f NAME --apply` targeting only
  source-symlink skipped entries exits 1 with the same warning and no
  mutation.
- **Repeated GC on same folder**: Running `gc -f <name> --apply` twice
  never mutates the quarantined copy. Because v1 scans only top-level
  model-root folders, the second run reports no managed folder matching
  `<name>` and exits 1.
- **Concurrent reconcile and gc**: Running `reconcile` after `gc --apply`
  may produce warnings for the now-missing quarantined folder's components
  (which is correct — the paths no longer exist). No data loss.
- **Restore from trash**: No restore command exists in v1. Users restore
  manually by moving the folder back from `.comfygo_trash/<date>/<name>/`
  to `$COMFYUI_MODELS_DIR/<name>/`.
- **Quarantine on read-only filesystem**: If the rename fails, GC reports
  the error and leaves the source unchanged.
- **Unsafe source folder name**: If a managed folder's name cannot be used
  as a safe quarantine path segment, filtered apply exits 1 with
  `error: Unsafe path segment: '<name>'; no files changed`, emits no
  traceback, leaves the source unchanged, creates no `.comfygo_trash/`,
  and does not rename the folder. Dry-run may still report the folder as
  managed because validation is only needed for quarantine destination
  construction. Short safe model-root names such as `<kind>-NNN` belong to
  a separate normalization/install behavior that preserves model identity in
  JSON metadata; GC does not perform that normalization.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `comfygo models gc` MUST be dry-run by default — no files
  are created, moved, or deleted without both `-f NAME` and `--apply`.
- **FR-002**: GC MUST only quarantine folders explicitly targeted via
  `-f NAME --apply`. GC MUST NOT quarantine all managed folders in bulk.
- **FR-003**: GC MUST report managed folders (have marker), ambiguous
  folders (no marker), and safety-relevant skipped entries such as source
  symlinks in the dry-run output. Reserved category folders and hidden
  folders MUST be skipped silently.
- **FR-004**: GC MUST skip reserved ComfyUI category folder names
  (same list as the model scanner), hidden dot-prefixed folders, and
  source entries that are symlinks.
- **FR-005**: On `-f NAME --apply`, GC MUST move the targeted folder to
  `.comfygo_trash/<YYYY-MM-DD>/<folder-name>/` using `os.rename()`.
  All path segments MUST be validated against symlink traversal
  (`validate_path_segment()`). The only filesystem mutation is the
  rename — no copying, no deleting. If a source folder name fails safe
  path-segment validation, GC MUST report a controlled error, perform no
  mutation, and MUST NOT normalize or rename the folder into the model
  root.
- **FR-006**: The `.comfygo_trash/` directory MUST be created
  automatically if it does not exist. GC MUST refuse to operate if
  `.comfygo_trash` is a symlink.
- **FR-007 (v1)**: GC MUST NOT prune, delete, or walk the contents of
  `.comfygo_trash/` for any purpose. The only mutations GC performs are:
  creating the dated trash directory when needed, and performing the
  explicit rename of one targeted source folder.
- **FR-008**: GC MUST be idempotent in effect — re-running
  `gc -f <name> --apply` after quarantine MUST NOT alter the quarantined
  copy or any other folder. Because the source is no longer in the
  top-level scan scope, the command reports no managed folder matching
  `<name>` and exits 1.
- **FR-009**: GC MUST NOT overlap with `reconcile` functionality.
  `reconcile` manages `.comfygo_views/` symlinks; `gc` manages
  real model folders. They are independent commands.
- **FR-010**: If the quarantine rename fails (e.g., permissions,
  cross-filesystem), GC MUST report the error and leave the source
  unchanged. Unsafe path-segment validation failures are handled the same
  way: clear error, no traceback, no source change, no trash creation. No
  copy+delete fallback — fail closed.
- **FR-011**: Destination collision: if `.comfygo_trash/<date>/<name>/`
  already exists, GC MUST append a suffix (`<name>-1`, `<name>-2`) and
  warn. Must never overwrite. Symlinks at the destination are treated as
  collisions.
- **FR-012**: A non-marker folder targeted via `-f NAME --apply` MUST be
  rejected — not quarantined.
- **FR-013**: When both `-f NAME` and `--apply` are supplied, GC MUST
  resolve the filter to exactly one managed folder. If zero managed
  matches, ambiguous-only matches, or multiple managed matches occur,
  GC MUST report the situation and perform no mutation.
- **FR-014**: GC MUST refuse to quarantine a source folder whose top-level
  directory entry is a symlink. Unfiltered dry-run MUST report
  `warning: Refusing to quarantine symlinked folder '<path>'`, exit 0,
  and perform no mutation. Filtered dry-run or `-f NAME --apply` targeting
  only source-symlink skipped entries MUST exit 1 with the same warning and
  perform no mutation.
- **FR-015 (v1)**: GC scans only top-level directories under the model
  root. GC does not scan legacy category children through `extra_roots`.
  GC does not recurse into subdirectories.
  **v1 Implementation Constraint**: The scan MUST use direct iteration
  (e.g. `models_dir.iterdir()`) and MUST NOT delegate folder discovery
  or classification to `scanner.scan_models()` or its `ambiguous` flag.
  The implementation MAY reuse scanner's reserved-folder policy for skip
  decisions only; it MUST NOT consume scanner package data or
  `packages.ambiguous`. This preserves raw symlink information and
  follows the plan decision for GC.

**CLI and Invocation Notes** (to support decomposition for implementation):
- The `gc` subcommand must be added to the argparse in cli.py alongside "reconcile".
- `--apply` without `-f NAME` MUST error with "error: --apply requires -f NAME" and exit 1 with no side effects.
- Error messages for apply must match the contracts (e.g. "No managed folder matching 'NAME'", "Filter 'NAME' matched multiple managed folders").
- Dry-run must print a structured report matching the example format (Managed, Ambiguous, Warnings) without creating .comfygo_trash/.
- CLI dispatch for `gc` MUST call the GC module with `models_dir`,
  `filter_str`, and `apply` only. It MUST NOT pass scanner package
  collections into GC.
- Empty report sections MUST be omitted. If no managed, ambiguous, or
  warning entries remain after filtering, GC MUST print exactly
  `Nothing to report.`
- Source symlink entries in unfiltered dry-run MUST be warnings but not
  command failures. A filtered dry-run or apply request targeting only
  source-symlink skipped entries MUST exit 1 with
  `warning: Refusing to quarantine symlinked folder '<path>'`.

### Repository Policy Requirements

- Features that invoke Python or comfy-cli commands MUST use uv-first
  command forms: `uv run`, `uv pip --python <workspace-python>`, or
  `uv run --python <workspace-python> --no-project python ...`.
- Features MUST NOT introduce direct `pip`, `python -m pip`, or unwrapped
  `python` workflow commands. If `uv` is missing, the feature must stop
  with an instruction to install `uv` first.
- No tokens, model files, generated views, caches, logs, user prompts, or
  local runtime state may be committed to this repo.
- Code and configuration files that reference model root paths MUST use
  configurable variables or environment variables (e.g.,
  `folder_paths.models_dir`), not hard-coded absolute paths, to keep the
  repo public-safe.

### Key Entities

- **Managed Folder**: A folder under the model root that contains at least
  one marker file (`.comfygo-download.json` or `comfygo-model.json`).
  Marker presence means "comfygo knows this folder" — it does NOT mean
  the folder is disposable. Only explicit `-f NAME --apply` targeting
  triggers quarantine.
- **Ambiguous Folder**: A folder under the model root with no marker file.
  GC reports it under "Ambiguous" but never moves it.
- **Skipped Entry**: A symlink entry, non-directory, or other
  safety-relevant entry that GC skips with a documented reason. Reserved
  category folders and hidden folders are skipped silently in user output.
- **Quarantine**: The action of moving a managed folder to
  `.comfygo_trash/<date>/<name>/` via `os.rename()`. Rename only — no
  copy-delete.
- **Normalization / Install Naming**: A separate non-GC behavior that may
  move downloaded managed folders into the model root under short safe names
  such as `<kind>-NNN`, while preserving model identity in JSON metadata.
  GC does not perform normalization.
- **GC Report**: The output of `comfygo models gc` — structured listing
  of managed, ambiguous, and skipped entries with warnings and errors.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A folder with `.comfygo-download.json` under the model root
  is listed as "Managed" in the dry-run output. Running
  `gc -f <folder> --apply` quarantines that folder only.
- **SC-002**: A folder with `comfygo-model.json` is treated identically
  to a downloader-marked folder.
- **SC-003**: Ambiguous folders (no marker) are reported but never moved,
  even when `--apply` is passed.
- **SC-004**: Reserved category folders and hidden folders are silently
  skipped.
- **SC-005**: Re-running `gc -f <folder> --apply` on an already‑
  quarantined folder exits 1 with a no-managed-match message and performs
  no filesystem mutation.
- **SC-006**: `.comfygo_trash/` is created automatically on first
  `--apply` if absent, and never created by a dry-run.
- **SC-007**: A failed quarantine (e.g., permission error) is reported
  without modifying the source folder.
- **SC-008**: Cross-filesystem quarantine is rejected with a clear error
  message and no files changed.
- **SC-009**: Ambiguous folders targeted with `-f NAME --apply` are
  rejected — not quarantined.
- **SC-010**: Multi-match `-f partial --apply` exits 1, lists all
  matches, moves nothing.
- **SC-011**: Source symlink folders are skipped and never quarantined.
- **SC-012**: A dry-run GC scan over approximately 100 top-level model
  folders in a temporary model root completes in under 1 second without
  creating `.comfygo_trash/`.

## Assumptions

- The model root defaults to ComfyUI's `folder_paths.models_dir`,
  consistent with the existing model registry feature.
- The `.comfygo_trash/` directory lives on the same filesystem as the
  model root. Cross-filesystem quarantine is explicitly rejected.
- Marker-based ownership means "comfygo has seen this folder," not
  "this folder is disposable." The user must explicitly name folders
  to quarantine.
- GC v1 scans only top-level model root folders. No legacy category
  recursion.
- No automatic restore command exists in v1. Users restore manually.
- GC is an independent command and does not run automatically during
  `comfygo`, `comfygo start`, `comfygo restart`, or `comfygo doctor`.
- The existing reconcile command handles `.comfygo_views/` stale symlink
  pruning independently and is not affected by GC.
