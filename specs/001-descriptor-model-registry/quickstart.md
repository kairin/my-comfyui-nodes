# Quickstart: Descriptor-First Model Registry

**Validation guide** for confirming the feature works end-to-end.

## Prerequisites

- A local ComfyUI installation with `COMFYUI_DIR` set in your `.envrc.local`
- `uv` installed
- This repo synced into the live ComfyUI (`comfygo sync` applied)
- The `comfygo_model_registry` node present in `custom_nodes/`

## Setup

```bash
cd REPO_ROOT
direnv allow   # if not already done
```

## Validation Scenarios

### Scenario 1: Diffusers Package Detection

1. Prepare a test Diffusers-style model folder:

   ```bash
   TEST_DIR="$COMFYUI_DIR/models/.test-models"
   mkdir -p "$TEST_DIR/TestModel-001/transformer" \
            "$TEST_DIR/TestModel-001/text_encoder" \
            "$TEST_DIR/TestModel-001/vae"
   echo '{"model_index": true}' > "$TEST_DIR/TestModel-001/model_index.json"
   ```

2. Configure the model root to include the test directory and run the scanner:

   ```bash
   COMFYGO_MODEL_REGISTRY_AUTORUN=0 uv run python -c "
   from custom_nodes.comfygo_model_registry.scanner import scan_models
   packages = scan_models('$TEST_DIR')
   for p in packages:
       print(f'{p.name}: kind={p.kind}, components={len(p.components)}, ambiguous={p.ambiguous}')
   "
   ```

3. **Expected**: `TestModel-001: kind=diffusers, components=3, ambiguous=False`

### Scenario 2: CLI Model Listing

1. Run:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR"
   ```

2. **Expected**: Output shows model root, 1 identified package, 0 ambiguous.

3. Run:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR" -f TestModel
   ```

4. **Expected**: Output shows `TestModel-001` canonical path and which categories
   can see `transformer`, `text_encoder`, and `vae`. Running
   `scripts/comfygo-models.sh --models-dir "$TEST_DIR"` (no filter) shows
   summary: model root, 1 identified, 0 ambiguous.

### Scenario 3: Dry-Run Reconcile

1. Run:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile
   ```

2. **Expected**: Output reports what symlinks would be created under
   `$TEST_DIR/.comfygo_views/`. No files are written.

### Scenario 4: Apply Reconcile

1. Run:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile --apply
   ```

2. **Expected**: Symlinks are created:

   ```bash
   ls -la "$TEST_DIR/.comfygo_views/diffusion_models/TestModel-001/"
   # → transformer -> ../../TestModel-001/transformer
   ls -la "$TEST_DIR/.comfygo_views/text_encoders/TestModel-001/"
   # → text_encoder -> ../../TestModel-001/text_encoder
   ls -la "$TEST_DIR/.comfygo_views/vae/TestModel-001/"
   # → vae -> ../../TestModel-001/vae
   ```

### Scenario 5: Idempotency Check

1. Run apply again:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile --apply
   ```

2. **Expected**: Output reports that all existing symlinks are unchanged.
   Current output may summarize this as "Nothing to do — all views are up to
   date." No errors. Symlinks intact.

### Scenario 6: Stale Symlink Pruning

1. Remove the model folder:

   ```bash
   rm -rf "$TEST_DIR/TestModel-001"
   ```

2. Run reconcile with apply:

   ```bash
   scripts/comfygo-models.sh --models-dir "$TEST_DIR" reconcile --apply
   ```

3. **Expected**: `.comfygo_views/` is empty or does not exist (all stale entries
   pruned).

### Scenario 7: Ambiguous Folder Rejection

1. Create an ambiguous folder:

   ```bash
   mkdir -p "$TEST_DIR/MysteryModel"
   echo "not-a-descriptor" > "$TEST_DIR/MysteryModel/random.safetensors"
   ```

2. Run scan:

   ```bash
   COMFYGO_MODEL_REGISTRY_AUTORUN=0 uv run python -c "
   from custom_nodes.comfygo_model_registry.scanner import scan_models
   packages = scan_models('$TEST_DIR')
   ambiguous = [p for p in packages if p.ambiguous]
   print(f'Ambiguous folders: {len(ambiguous)}')
   for p in ambiguous:
       print(f'  {p.name}')
   "
   ```

3. **Expected**: `MysteryModel` appears as ambiguous, no symlinks created.

### Scenario 8: ComfyUI Startup Integration

1. Ensure the real model root has at least one identifiable package.
2. Run:

   ```bash
   comfygo restart
   ```

3. **Expected**: Before ComfyUI launches, `.comfygo_views/` is updated. After
   launch, ComfyUI nodes that browse `diffusion_models`, `text_encoders`, or
   `vae` can select the detected model components.

### Cleanup

```bash
rm -rf "$TEST_DIR"
```

## Tests

Run the automated test suite:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest custom_nodes/comfygo_model_registry/tests -q
```

**Expected**: All tests pass.
