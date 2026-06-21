# Quickstart: Model Garbage Collection

**Validation guide** for confirming the GC feature works safely.

## Prerequisites

- The comfygo model registry (feature 001) must be installed and synced
- `uv` installed
- A writable model root with at least one Diffusers-style model folder

## Setup

Always use a temp directory for validation tests:

```bash
MODELS_DIR="$(mktemp -d /tmp/comfygo-gc.XXXXXX)"
echo "MODELS_DIR=$MODELS_DIR"
```

## Validation Scenarios

### Scenario 1: Dry-Run Report

1. Create a managed folder with a download marker:

   ```bash
   mkdir -p "$MODELS_DIR/TestModel"
   printf '{"schema":"comfygo.download.v1","repo":"example/model"}\n' \
     > "$MODELS_DIR/TestModel/.comfygo-download.json"
   ```

2. Run GC dry-run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR"
   ```

3. **Expected**: Output lists `TestModel` under "Managed folders."
   No `.comfygo_trash/` directory is created.

### Scenario 2: Ambiguous Folder Reporting

1. Create a folder with no marker:

   ```bash
   mkdir "$MODELS_DIR/Untagged"
   ```

2. Run GC dry-run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR"
   ```

3. **Expected**: `Untagged` appears under "Ambiguous." Both `TestModel`
   and `Untagged` are reported. No files moved.

### Scenario 3: Quarantine With Explicit Target

1. Run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f TestModel --apply
   ```

2. **Expected**:
   - `TestModel` is moved to `.comfygo_trash/<date>/TestModel/`
   - The original path no longer exists under `$MODELS_DIR`
   - `Untagged` is untouched

### Scenario 4: Ambiguous Folder Rejection

1. Run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f Untagged --apply
   ```

2. **Expected**: Error: "Folder 'Untagged' is not managed by comfygo."
   No files changed.

### Scenario 5: Multi-Match Safety

1. Create two managed folders sharing a common prefix:

   ```bash
   mkdir "$MODELS_DIR/ModelOne" "$MODELS_DIR/ModelTwo"
   printf '{"schema":"comfygo.download.v1"}\n' > "$MODELS_DIR/ModelOne/.comfygo-download.json"
   printf '{"schema":"comfygo.download.v1"}\n' > "$MODELS_DIR/ModelTwo/.comfygo-download.json"
   ```

2. Run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f Model --apply
   ```

3. **Expected**: Error "matched multiple managed folders," lists both,
   moves neither.

### Scenario 6: Repeated Apply Safety

1. Run the quarantine from Scenario 3 again:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f TestModel --apply
   ```

2. **Expected**: Error about no managed folder matching `TestModel`. The
   already-quarantined folder under `.comfygo_trash/` is unchanged.

### Scenario 7: Missing Target

1. Run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f Nonexistent --apply
   ```

2. **Expected**: Error about no matching folder.

### Scenario 8: Unsafe Folder Name Fails Closed

1. Create a managed folder whose name cannot be used as a safe quarantine
   path segment:

   ```bash
   mkdir "$MODELS_DIR/~UnsafeModel"
   printf '{"schema":"comfygo.download.v1"}\n' \
     > "$MODELS_DIR/~UnsafeModel/.comfygo-download.json"
   ```

2. Run:

   ```bash
   scripts/comfygo-models.sh gc --models-dir "$MODELS_DIR" \
     -f '~UnsafeModel' --apply
   ```

3. **Expected**: Exit 1 with exactly:

   ```text
   error: Unsafe path segment: '~UnsafeModel'; no files changed
   ```

   There is no traceback, `~UnsafeModel` remains in place, and no new
   `.comfygo_trash/` directory is created for this failed operation. GC does
   not rename the folder into a short alias such as `<kind>-NNN`; that
   belongs to a separate normalization/install behavior.

## Doctor Script Matrix

Use `doctor-matrix.md` as the canonical matrix for scripting these checks as a
doctor-style harness. It assigns stable scenario IDs (`GCD-001` and onward),
fixture names, command lines, exit codes, required output fragments, and
mutation assertions.

The key boundary is:

- mutating GC checks run only against temp model roots
- live model-root checks are dry-run only
- live `--apply` is forbidden
- unexpected filesystem changes fail the doctor check

### Cleanup

```bash
rm -rf "$MODELS_DIR"
```

## Tests

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests -q
```

**Expected**: All tests pass (existing + new GC tests).
