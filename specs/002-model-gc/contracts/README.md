# Contracts: Model Garbage Collection

## CLI Interface

### `comfygo models gc`

Dry-run mode (default). Reports managed folders, ambiguous folders, and
safety warnings without modifying anything. Reserved category folders and
hidden folders are skipped silently.

**Exit code**: 0 (success), 1 (error)

**Output sections**: empty sections MUST be omitted. If no managed,
ambiguous, or warning entries remain after filtering, output exactly:

```text
Nothing to report.
```

When entries exist, use these sections:

```
Managed folders:
  <path>
    marker: <type>

Ambiguous:
  <path>
    no marker file found

Warnings:
  <message>
```

### `comfygo models gc -f/--filter <name>`

Filter the dry-run report to show only folders matching `<name>`.

**Exit code**: 0 (match found), 1 (no match)

### `comfygo models gc -f/--filter <name> --apply`

Quarantine the matching managed folder. Requires BOTH `-f NAME` and
`--apply`. The filter must resolve to exactly one managed folder.

**Exit code**: 0 (quarantine completed), 1 (error)

### Error messages and exit codes

| Scenario | Exit | Message |
|----------|------|---------|
| `gc -f NAME`, no visible match | 1 | `error: No folders matching 'NAME'` |
| `gc --apply` without `-f` | 1 | `error: --apply requires -f NAME` |
| `gc -f NAME --apply`, no managed match | 1 | `error: No managed folder matching 'NAME'` |
| `gc -f NAME --apply`, ambiguous-only match | 1 | `error: Folder 'NAME' is not managed by comfygo` |
| `gc -f NAME --apply`, multiple managed matches | 1 | `error: Filter 'NAME' matched multiple managed folders` (then list each) |
| Source symlink in unfiltered dry-run | 0 | `warning: Refusing to quarantine symlinked folder '<path>'` |
| `gc -f NAME` matches only source-symlink skipped entries | 1 | `warning: Refusing to quarantine symlinked folder '<path>'` |
| `gc -f NAME --apply` targets a source-symlink skipped entry | 1 | `warning: Refusing to quarantine symlinked folder '<path>'` |
| `gc -f NAME --apply`, unsafe quarantine path segment | 1 | `error: Unsafe path segment: '<name>'; no files changed` |
| Cross-filesystem rename fails (EXDEV) | 1 | `error: Cannot quarantine across filesystems; no files changed` |
| Permission error on rename | 1 | `error: Permission denied: <path>; no files changed` |

### Safety rules

- Without `-f`, GC never modifies the filesystem, even with `--apply`.
- Without `--apply`, GC never modifies the filesystem, even with `-f`.
- Both flags required for any mutation.
- With both flags, the `-f` filter must resolve to exactly one managed
  folder. Zero, ambiguous-only, or multiple matches produce an error and
  no mutation.
- Re-running `gc -f NAME --apply` after a successful quarantine produces the
  same no-managed-match error because the original top-level source is gone;
  it must not alter the quarantined copy.
- The only allowed mutation is `os.rename()`. No copy+delete fallback.
- Source symlinks in unfiltered dry-run do not make the command fail:
  exit 0, report a warning, no mutation.
- Filtered dry-run or apply targeting only source-symlink skipped entries
  exits 1 with the same warning and no mutation.
- `.comfygo_trash` root refused if it is a symlink.
- Source folder names that fail safe path-segment validation fail with a
  controlled error, no traceback, no source mutation, and no trash creation.
- GC does not normalize downloaded folders into short root aliases such as
  `<kind>-NNN`; that belongs to a separate install/normalization behavior.

### Marker Schema

#### `.comfygo-download.json`

File created by the HF download helper. Schema: `comfygo.download.v1`.
Presence marks the folder as managed by comfygo. The file's existence
alone is sufficient ownership proof — the content may be unparseable.

#### `comfygo-model.json`

Descriptor file (schema `comfygo.model.v1`). Presence marks the folder
as managed, regardless of whether the descriptor parses correctly.

### Quarantine constraints

- Only `os.rename()` — no copy+delete fallback.
- Cross-filesystem rename fails with clear error, no mutation.
- Source symlink refused.
- `.comfygo_trash` symlink refused.
- Destination collision: append `-1`, `-2` suffix, never overwrite.
- Treat all existing destination paths (directory, file, symlink, broken
  symlink) as collisions — never merge or write through.
- Unsafe destination path segments fail before creating trash directories.
- GC v1 does not prune or maintain `.comfygo_trash` contents. It refuses
  to operate if required trash path components are symlinks.
