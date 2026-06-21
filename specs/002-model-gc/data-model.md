# Data Model: Model Garbage Collection

## Entities

### ManagedFolder

A folder under the model root that contains at least one ownership marker
file. Managed does not mean disposable — only explicit `-f NAME --apply`
targeting triggers quarantine.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| name | str | Folder name (last path component) | Yes |
| path | Path | Absolute raw path under model root | Yes |
| markers | list[Marker] | Detected marker files | Yes |

Validation: `name` may be any existing top-level folder name for dry-run
reporting, but quarantine destination construction must validate it with the
shared path-segment rules. If validation fails, apply records a controlled
error and performs no mutation.

### Marker

An ownership proof file discovered during GC scan.

| Field | Type | Description |
|-------|------|-------------|
| type | str | `downloader` (`.comfygo-download.json`) or `descriptor` (`comfygo-model.json`) |
| path | Path | Absolute path to the marker file |
| parseable | bool | True if the marker JSON is valid |

### AmbiguousFolder

A folder under the model root with no marker file. Never moved.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Folder name |
| path | Path | Absolute raw path under model root |
| reason | str | Always `"no marker file found"` |

### SkippedFolder

A folder or entry that was skipped during GC scan. Never moved. Some skipped
entries, such as reserved and hidden folders, may be kept internal and omitted
from user-facing output.

| Field | Type | Description |
|-------|------|-------------|
| name | str | Entry name |
| path | Path | Absolute raw path |
| reason | str | `"reserved folder"`, `"hidden folder"`, `"source symlink"`, `"non-directory"`, or `"outside scan scope"` |

### QuarantineOperation

A single folder quarantine that was performed (apply).

| Field | Type | Description |
|-------|------|-------------|
| source | Path | Original raw path under model root |
| destination | Path | Path under `.comfygo_trash/<date>/<name>/` |
| status | str | `completed`, `skipped`, or `failed` |
| reason | str | Why skipped or why failed |

### GCReport

The output of a full GC pass.

| Field | Type | Description |
|-------|------|-------------|
| managed | list[ManagedFolder] | Folders eligible for explicit quarantine |
| ambiguous | list[AmbiguousFolder] | Folders with no marker |
| skipped | list[SkippedFolder] | Folders skipped for safety/scope reasons; user output may omit silent skip categories |
| operations | list[QuarantineOperation] | What was done (empty in dry-run) |
| apply_requested | bool | Whether `--apply` was passed |
| apply_filter | str or None | The `-f` filter value, if any |
| selected_target | ManagedFolder or None | The single managed match for apply (if unique) |
| errors | list[str] | Fatal issues that blocked operation |

### Normalization / Install Naming (out of GC scope)

Downloaded managed folders may later be normalized into short model-root
names such as `<kind>-NNN`, with JSON metadata preserving the original model
identity. That lifecycle is not part of GC. GC never performs this
normalization; it reports unsafe quarantine names as controlled errors.
