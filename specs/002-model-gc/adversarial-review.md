# Adversarial Review And Implementation Handoff: 002-model-gc

**Date**: 2026-06-20

**Feature**: `specs/002-model-gc`

**Target reader**: The next agent that will implement `comfygo models gc`.

**Status**: Ready for implementation after the remediation pass. Start with
the dry-run MVP (Setup + Foundational + US2) before implementing quarantine.

---

## 1. Final Verdict

The original adversarial review found serious safety gaps. Those gaps have now
been folded into the live feature documents:

- `spec.md`
- `plan.md`
- `tasks.md`
- `data-model.md`
- `contracts/README.md`
- `quickstart.md`
- `research.md`
- `checklists/requirements.md`

The feature is now safe enough to implement if the implementer follows the
current docs literally.

The implementation must preserve this rule:

```text
GC is an explicit single-folder quarantine tool, not an automatic cleanup tool.
```

Safe command shape:

```text
comfygo models gc
    Dry-run report only. No filesystem mutation.

comfygo models gc -f NAME
    Filtered dry-run report only. No filesystem mutation.

comfygo models gc --apply
    Error. No filesystem mutation because -f NAME is missing.

comfygo models gc -f NAME --apply
    Quarantine exactly one matching managed folder only if the match is unique
    and all safety checks pass.
```

---

## 2. What Was Fixed

The review items below are now represented in the implementation-facing docs.

| Safety issue | Current resolution |
|--------------|--------------------|
| Marker meant "garbage" | Fixed. Marker means "known by comfygo", not disposable. |
| Bulk quarantine risk | Fixed. `--apply` requires `-f NAME`; no bulk operation in v1. |
| Multi-match ambiguity | Fixed. `-f NAME --apply` must resolve to exactly one managed folder. |
| Trash pruning copy-paste | Fixed. `FR-007` now says GC must not prune/delete/walk `.comfygo_trash/`. |
| Copy-delete fallback | Fixed. Rename-only via `os.rename()`; fail closed on `EXDEV`. |
| Source symlink risk | Fixed. Source symlink folders are refused. |
| Resolved scanner path risk | Fixed. GC uses raw top-level `models_dir.iterdir()` entries, not `scanner.scan_models()` paths. |
| Legacy folder movement risk | Fixed. v1 scans only top-level model-root folders; no legacy `extra_roots`. |
| Bad data model | Fixed. `Marker` typo corrected; `ManagedFolder.ambiguous` removed; `SkippedFolder` added. |
| Missing safety tests | Fixed in tasks. T036 invalid marker, T037 multi-match apply, T038 source symlink, T039 apply-without-filter. |

---

## 3. Non-Negotiable Safety Principles

### 3.1 Marker Does Not Mean Disposable

Marker files:

```text
.comfygo-download.json
comfygo-model.json
```

mean only:

```text
comfygo knows this folder exists
```

They do not mean:

```text
this folder is unused
this folder is garbage
this folder should be moved automatically
```

Therefore, the implementation must never quarantine every marked folder.

### 3.2 Dry-Run Must Be Truly Read-Only

These commands must not create `.comfygo_trash/` and must not mutate anything:

```bash
scripts/comfygo-models.sh --models-dir "$MODELS_DIR" gc
scripts/comfygo-models.sh --models-dir "$MODELS_DIR" gc -f NAME
scripts/comfygo-models.sh --models-dir "$MODELS_DIR" gc --apply
```

`gc --apply` exits 1 because `-f NAME` is missing, but it still must not create
or change any file.

### 3.3 Apply Requires Exactly One Managed Match

Apply mode requires:

```text
-f NAME
--apply
```

Then the filter must resolve to exactly one managed folder.

Required outcomes:

```text
0 managed matches -> exit 1, no mutation
1 managed match -> allowed after safety checks
2+ managed matches -> exit 1, list matches, no mutation
ambiguous-only match -> exit 1, no mutation
```

Never choose the first match.

### 3.4 Quarantine Is Rename-Only

The only allowed move operation is:

```text
os.rename(source, destination)
```

Forbidden:

```text
shutil.move()
shutil.copytree()
copy then delete
rsync then delete
manual recursive copy
automatic deletion of model files
```

If `os.rename()` fails, report the error and leave the source unchanged.

### 3.5 `.comfygo_trash/` Is Not `.comfygo_views/`

`.comfygo_views/` is generated and disposable.

`.comfygo_trash/` contains real quarantined model folders.

GC v1 must not:

- prune `.comfygo_trash/`
- walk `.comfygo_trash/`
- delete anything inside `.comfygo_trash/`
- maintain trash contents

The only allowed trash mutation is creating the dated destination directory
needed for a successful apply operation.

### 3.6 Symlink Safety

GC must refuse or avoid symlink-sensitive paths:

- source folder is a symlink -> refuse
- `.comfygo_trash` is a symlink -> refuse
- `.comfygo_trash/<date>` is a symlink -> refuse
- destination path exists as a symlink -> treat as collision, never write through
- generated path segment is unsafe -> refuse

Use `lstat`/`is_symlink()` before any operation that may follow symlinks.

### 3.7 GC Is Manual Only

GC must not run from:

```text
comfygo
comfygo start
comfygo restart
comfygo doctor
ComfyUI import/startup
```

It is a manual subcommand only.

---

## 4. Current Implementation Contract

The implementation must match these current docs.

### Scope

GC v1 scans only top-level entries directly under the configured model root.

It must not scan or quarantine children under legacy category folders such as:

```text
diffusers/
diffusion_models/
loras/
vae/
text_encoders/
checkpoints/
```

### Classification

Use raw top-level entries:

```text
for entry in sorted(models_dir.iterdir()):
```

Do not use `scanner.scan_models()` for GC move-source discovery. Scanner output
resolves package paths and is unsafe as the source of a rename operation.

Classification:

```text
hidden dot-prefixed entry -> skip silently
reserved category folder -> skip silently
source symlink -> report safety warning / skipped source symlink
non-directory -> skip
directory with .comfygo-download.json -> managed
directory with comfygo-model.json -> managed
directory without marker -> ambiguous
```

Marker parse result:

```text
parseable JSON -> parseable=true
empty/invalid JSON -> parseable=false + warning, still managed
```

### Dry-Run Output

Dry-run must be readable and stable enough for tests:

```text
Managed folders:
  <path>
    marker: <type>

Ambiguous:
  <path>

Warnings:
  <path>: <message>
```

Reserved and hidden folders are not printed as ambiguous.

### Apply Output And Errors

Required errors from `contracts/README.md`:

```text
gc --apply
    exit 1
    error: --apply requires -f NAME

gc -f NAME --apply, no managed match
    exit 1
    error: No managed folder matching 'NAME'

gc -f NAME --apply, ambiguous-only match
    exit 1
    error: Folder 'NAME' is not managed by comfygo

gc -f NAME --apply, multiple managed matches
    exit 1
    error: Filter 'NAME' matched multiple managed folders

source symlink
    exit 1
    warning: Refusing to quarantine symlinked folder '<path>'

cross-filesystem rename
    exit 1
    error: Cannot quarantine across filesystems; no files changed
```

Repeated apply after a successful quarantine:

```text
gc -f NAME --apply
    first run: moves source into .comfygo_trash/<date>/NAME
    second run: source no longer appears in top-level scan
    result: exit 1, no managed folder matching NAME, no mutation
```

This is the correct v1 behavior.

---

## 5. Recommended Implementation Order

Follow `tasks.md`, but keep this order strict.

### Phase A: Setup

Implement only:

- `custom_nodes/comfygo_model_registry/gc.py`
- `custom_nodes/comfygo_model_registry/tests/test_gc.py`
- CLI parser shape
- wrapper forwarding verification

No quarantine behavior yet.

### Phase B: Foundational Scan And Marker Detection

Implement:

- raw top-level scan
- marker detection
- reserved/hidden skip behavior
- source symlink refusal/reporting
- destination path helper skeleton

Tests should prove dry-run creates no `.comfygo_trash/`.

### Phase C: US2 Dry-Run MVP

Complete all US2 tasks and stop.

Run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests/test_gc.py -q
```

Only after dry-run behavior is correct should apply/quarantine be implemented.

### Phase D: US3 Apply

Implement:

- apply gate
- unique managed match selection
- collision handling
- source/trash symlink refusal
- `os.rename()` only
- `EXDEV`/permission fail-closed handling

---

## 6. Required Tests

At minimum, the implementation must cover these cases.

### Dry-Run

- empty root -> "nothing to report", exit 0, no `.comfygo_trash`
- `.comfygo-download.json` marker -> managed
- `comfygo-model.json` marker -> managed
- empty/invalid marker -> managed + warning
- ambiguous folder -> ambiguous
- reserved category folder -> not shown as ambiguous
- hidden folder -> not shown as ambiguous
- source symlink -> reported/refused and never quarantined
- `gc -f NAME` -> filtered dry-run only

### Apply Gate

- `gc --apply` -> exit 1, no `.comfygo_trash`
- `gc -f NAME` -> dry-run only
- `gc -f Missing --apply` -> exit 1, no mutation
- `gc -f Ambiguous --apply` -> exit 1, no mutation
- `gc -f partial --apply` with two managed matches -> exit 1, list matches, no mutation
- `gc -f unique --apply` -> moves only that folder

### Quarantine

- successful quarantine moves one folder into `.comfygo_trash/<date>/<name>`
- source is gone after successful quarantine
- contents are unchanged after rename
- other folders are untouched
- second apply after quarantine exits 1 and does not alter trash
- destination collision appends suffix and never overwrites
- destination symlink is never written through
- `.comfygo_trash` symlink is refused
- `.comfygo_trash/<date>` symlink is refused
- `os.rename` raising `EXDEV` leaves source unchanged
- `os.rename` raising `PermissionError` leaves source unchanged

### Integration

- `scripts/comfygo-models.sh --models-dir "$TMP" gc`
- `scripts/comfygo-models.sh --models-dir "$TMP" gc -f NAME`
- `scripts/comfygo-models.sh --models-dir "$TMP" gc -f NAME --apply`
- `scripts/comfygo-models.sh --models-dir "$TMP" gc --apply`
- `scripts/comfygo doctor` remains reconcile-only and unaffected by GC
- existing model registry tests still pass

---

## 7. Verification Commands

Before implementation:

```bash
rg -n "ScanResults|list\\[Maker\\]|ambiguous \\| bool|shutil.move|shutil.copytree|copy then delete|copy\\+delete fallback" specs/002-model-gc
```

Expected: no implementation-facing stale instructions. Historical references
inside this review are acceptable only if they are clearly warning against the
old behavior.

After implementation:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests -q
bash -n scripts/comfygo-models.sh
bash -n scripts/comfy-local
git diff --check
```

Manual probe with a temp model root:

```bash
TEST_DIR="$(mktemp -d /tmp/comfygo-gc.XXXXXX)"
mkdir -p "$TEST_DIR/ManagedOne" "$TEST_DIR/ManagedTwo" "$TEST_DIR/Untagged"
printf '{"schema":"comfygo.download.v1","repo":"example/one"}\n' > "$TEST_DIR/ManagedOne/.comfygo-download.json"
printf '{"schema":"comfygo.download.v1","repo":"example/two"}\n' > "$TEST_DIR/ManagedTwo/.comfygo-download.json"

UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-models.sh --models-dir "$TEST_DIR" gc
test ! -e "$TEST_DIR/.comfygo_trash"

UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-models.sh --models-dir "$TEST_DIR" gc --apply
test ! -e "$TEST_DIR/.comfygo_trash"

UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-models.sh --models-dir "$TEST_DIR" gc -f Managed --apply
test -d "$TEST_DIR/ManagedOne"
test -d "$TEST_DIR/ManagedTwo"
test ! -e "$TEST_DIR/.comfygo_trash"

UV_CACHE_DIR=/tmp/uv-cache scripts/comfygo-models.sh --models-dir "$TEST_DIR" gc -f ManagedOne --apply
test ! -e "$TEST_DIR/ManagedOne"
test -d "$TEST_DIR/ManagedTwo"
find "$TEST_DIR/.comfygo_trash" -maxdepth 3 -type d -name ManagedOne | grep ManagedOne
```

---

## 8. What Not To Do

Do not:

- implement bulk quarantine
- make `gc --apply` operate without `-f`
- choose the first match when multiple folders match
- use `scanner.scan_models()` as the source of paths to rename
- use resolved symlink targets as source paths
- use `shutil.move`
- use copy-delete fallback
- move legacy category children in v1
- follow source symlinks
- write through trash symlinks
- create `.comfygo_trash/` in dry-run
- modify `.comfygo_views/` from GC
- change `doctor` to run GC
- run GC during startup
- delete real model folders

---

## 9. Plain-Language Summary

This feature is like a safe "move this one folder out of the way" command.

A marker file is like a name tag. It proves comfygo recognizes the folder. It
does not prove the folder is trash.

That is why this is safe:

```bash
comfygo models gc -f ExactFolder --apply
```

and this must never move anything:

```bash
comfygo models gc --apply
```

Implementation should be conservative. When unsure, refuse to move and explain
why.
