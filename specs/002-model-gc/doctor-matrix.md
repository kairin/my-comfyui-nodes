# GC Doctor Matrix

This matrix is the canonical source for scripting GC safety checks as a
doctor-style validation harness.

The harness MUST run all GCD mutating validation scenarios in a temporary model
root. It MUST NOT run scenario `--apply` checks against the real ComfyUI model
root. Live runtime validation performed by this matrix is read-only only.

## Harness Defaults

Use these defaults for every scripted run:

```bash
export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export PYTHONDONTWRITEBYTECODE=1
WRAPPER="scripts/comfygo-models.sh"
MODELS_DIR="$(mktemp -d /tmp/comfygo-gc-doctor.XXXXXX)"
```

For every temp-root scenario, capture:

- command line
- exit code
- stdout
- stderr
- pre/post filesystem snapshot under `$MODELS_DIR`
- whether `.comfygo_trash/` exists

For failure cases, the source folder MUST remain in place and no new trash
directory may be created unless the case explicitly expects a successful
quarantine.

## Fixture Names

Use these exact folder names so output assertions are stable:

| Fixture | Setup |
|---------|-------|
| `ManagedDownloader` | directory with `.comfygo-download.json` containing valid JSON |
| `ManagedDescriptor` | directory with `comfygo-model.json` containing valid JSON |
| `AmbiguousOnly` | directory with no marker file |
| `ModelOne`, `ModelTwo` | managed downloader folders used for multi-match tests |
| `LinkedModel` | source symlink to a managed folder outside `$MODELS_DIR` |
| `~UnsafeModel` | managed downloader folder with an unsafe quarantine path segment |
| `diffusion_models`, `loras`, `.hidden_folder`, `.comfygo_views` | reserved or hidden folders |

## Temp-Root Scenarios

| ID | Setup | Command | Exit | Required Output | Mutation Assertion |
|----|-------|---------|------|-----------------|-------------------|
| GCD-001 | Empty `$MODELS_DIR` | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | exactly `Nothing to report.` | no `.comfygo_trash/` |
| GCD-002 | `ManagedDownloader` | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | `Managed folders:` and `marker: downloader` | no `.comfygo_trash/` |
| GCD-003 | `ManagedDescriptor` | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | `Managed folders:` and `marker: descriptor` | no `.comfygo_trash/` |
| GCD-004 | `AmbiguousOnly` | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | `Ambiguous:` and `no marker file found` | source unchanged |
| GCD-005 | reserved and hidden folders only | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | exactly `Nothing to report.` | skipped folders unchanged |
| GCD-006 | `LinkedModel` source symlink | `$WRAPPER --models-dir "$MODELS_DIR" gc` | 0 | `warning: Refusing to quarantine symlinked folder` | symlink unchanged, no trash |
| GCD-007 | `LinkedModel` source symlink | `$WRAPPER --models-dir "$MODELS_DIR" gc -f LinkedModel` | 1 | same symlink refusal warning | symlink unchanged, no trash |
| GCD-008 | `LinkedModel` source symlink | `$WRAPPER --models-dir "$MODELS_DIR" gc -f LinkedModel --apply` | 1 | same symlink refusal warning | symlink unchanged, no trash |
| GCD-009 | `ManagedDownloader` | `$WRAPPER --models-dir "$MODELS_DIR" gc --apply` | 1 | `error: --apply requires -f NAME` | source unchanged, no trash |
| GCD-010 | `ManagedDownloader` | `$WRAPPER --models-dir "$MODELS_DIR" gc -f Missing --apply` | 1 | `error: No managed folder matching 'Missing'` | source unchanged, no trash |
| GCD-011 | `AmbiguousOnly` | `$WRAPPER --models-dir "$MODELS_DIR" gc -f AmbiguousOnly --apply` | 1 | `error: Folder 'AmbiguousOnly' is not managed by comfygo` | source unchanged, no trash |
| GCD-012 | `ModelOne`, `ModelTwo` | `$WRAPPER --models-dir "$MODELS_DIR" gc -f Model --apply` | 1 | `error: Filter 'Model' matched multiple managed folders` plus both paths | both sources unchanged, no trash |
| GCD-013 | `~UnsafeModel` | `$WRAPPER --models-dir "$MODELS_DIR" gc -f '~UnsafeModel' --apply` | 1 | `error: Unsafe path segment: '~UnsafeModel'; no files changed`; no `Traceback` | source unchanged, no trash |
| GCD-014 | `ManagedDownloader` | `$WRAPPER --models-dir "$MODELS_DIR" gc -f ManagedDownloader --apply` | 0 | `Quarantined:` and `.comfygo_trash/<date>/ManagedDownloader` | source gone, exactly one trash folder created |
| GCD-015 | after GCD-014 | `$WRAPPER --models-dir "$MODELS_DIR" gc -f ManagedDownloader --apply` | 1 | `error: No managed folder matching 'ManagedDownloader'` | quarantined folder unchanged |
| GCD-016 | `ManagedDownloader`, wrapper flag after subcommand | `$WRAPPER gc --models-dir "$MODELS_DIR"` | 0 | same as GCD-002 | no `.comfygo_trash/` |

## Automated Regression Scenarios

The doctor harness should call the existing test suite rather than duplicate
every Python-level assertion in shell:

```bash
UV_CACHE_DIR=/tmp/uv-cache PYTHONDONTWRITEBYTECODE=1 \
  uv run pytest custom_nodes/comfygo_model_registry/tests -q --tb=line \
  -p no:cacheprovider
```

Required coverage delegated to pytest:

- `scanner.scan_models()` is not called by GC discovery.
- Dry-run over roughly 100 top-level folders completes in under 1 second.
- Rename failure paths leave sources unchanged.
- Destination collisions use suffixes and never overwrite.
- `.comfygo_trash` and dated trash symlinks are refused.
- `os.rename()` is the only apply move primitive.
- Existing reconcile behavior remains independent.

## Live Runtime Read-Only Smoke

The live smoke is optional unless a real model root is configured. It is always
read-only.

Command:

```bash
$WRAPPER --models-dir "$LIVE_MODELS_DIR" gc
```

Required assertions:

- exit 0, unless the live root itself is unreadable
- no `--apply` is used
- no `.comfygo_trash/` directory is created if it was absent before
- if `.comfygo_trash/` existed before, its metadata and contents are unchanged
- reserved ComfyUI category folders such as `diffusion_models`, `loras`,
  `vae`, `text_encoders`, and `checkpoints` are not listed under `Ambiguous:`

## Doctor Integration Boundary

Default `comfygo doctor` should continue checking registry/reconcile health.
A GC doctor check may be added as a separate doctor section or explicit
development check, but it must obey this matrix:

- temp-root apply checks are allowed
- live-root dry-run checks are allowed
- live-root apply checks are forbidden for this GCD validation harness
- any unexpected filesystem change is a failure

Feature `003-gc-doctor` defines a separate guided user action for live
`targeted-gc`. That action is outside this matrix's validation scenarios and
must have its own explicit target, readiness, and confirmation contract.
