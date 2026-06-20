# Data Model: Descriptor-First Model Registry

## Entities

### ModelPackage

A folder under the model root that is self-identifying as a model.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `name` | `str` | Folder name — unique identifier | always |
| `path` | `Path` | Absolute path to the model folder | always |
| `kind` | `ModelKind` | Classification: `diffusers`, `lora`, `embedding`, `checkpoint`, `vae`, `text_encoder`, `controlnet`, `gguf`, `other` | always |
| `source` | `ModelSource` | Origin metadata (optional for ambiguous) | when descriptor present |
| `components` | `list[Component]` | Recognized sub-components of this package | always (may be empty) |
| `descriptor` | `Descriptor` | Parsed `comfygo-model.json` (if present) | optional |
| `detection_method` | `DetectionMethod` | How the package was identified: `descriptor`, `diffusers_inference`, `unknown` | always |
| `ambiguous` | `bool` | True when the folder cannot be identified | always |

**Validation rules**:
- `name` must be a valid POSIX directory name
- `path` must exist and be a directory
- Two packages with the same `name` at different `path` values are a conflict
- `components` must have unique logical names within a package

### ModelKind

Enumeration of recognized model types.

Values: `diffusers`, `lora`, `embedding`, `checkpoint`, `vae`, `text_encoder`,
`controlnet`, `gguf`, `other`

### DetectionMethod

Enumeration describing how a model was identified.

Values: `descriptor`, `diffusers_inference`, `unknown`

### ModelSource

Metadata about where a model originated.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `type` | `str` | `huggingface`, `civitai`, `local`, or other | when descriptor |
| `repo` | `str` | Source repo/URL/model ID | optional |
| `version` | `str` | Version ID or commit SHA | optional |

### Component

A subdirectory or file within a model package that maps to ComfyUI categories.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `logical_name` | `str` | Human-readable name (e.g., `transformer`, `text_encoder`, `vae`) | always |
| `relative_path` | `Path` | Path relative to the package root | always |
| `comfy_categories` | `list[str]` | ComfyUI category names (e.g., `diffusion_models`, `text_encoders`) | always |
| `resolved_path` | `Path` | Absolute path after joining with package path | computed |
| `exists` | `bool` | Whether the component path actually exists on disk | computed |

**Validation rules**:
- `relative_path` must stay inside the package directory (no `../` escape)
- `comfy_categories` must not be empty
- Each `comfy_category` must be a known ComfyUI category or a valid custom category

### CompatibilityView

A generated symlink exposing a component to a ComfyUI category.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `category` | `str` | ComfyUI category name | always |
| `model_name` | `str` | Package name | always |
| `component_name` | `str` | Component logical name | always |
| `symlink_path` | `Path` | The generated symlink path | computed |
| `target_path` | `Path` | Where the symlink points | always |
| `is_valid` | `bool` | Whether the symlink target exists | computed |

### Descriptor

Parsed `comfygo-model.json` (schema `comfygo.model.v1`).

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `schema` | `str` | MUST be `"comfygo.model.v1"` | required |
| `name` | `str` | Model display name | required |
| `kind` | `str` | Model kind | required |
| `source` | `ModelSource` | Origin metadata | optional |
| `components` | `dict[str, ComponentDescriptor]` | Component definitions | required |
| `notes` | `str` | Free-text notes | optional |
| `workflows` | `list[str]` | Workflow file references | optional |
| `preview_images` | `list[str]` | Preview image file references | optional |
| `documentation` | `list[str]` | Documentation file references | optional |

### ComponentDescriptor

A component entry within a descriptor.

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `path` | `str` | Relative path within the package | required |
| `comfy_categories` | `list[str]` | Category names | required |

## State Transitions

### Model Package Lifecycle

```
discovered → identified (via descriptor or inference) → reconciled (symlinks exist)
                ↕
              ambiguous (no descriptor, no inference) → skipped
```

### Reconcile State Machine

```
initial state: no .comfygo_views/ exists
     │
     ├── reconcile --apply: create symlinks for all identified packages
     │                      → state: symlinks exist
     │
     ├── reconcile --apply (model removed): prune stale symlinks
     │                      → state: symlinks updated
     │
     ├── reconcile --apply (model added): create new symlinks
     │                      → state: symlinks updated
     │
     └── reconcile (dry-run): report without creating files
                              → state: unchanged
```

### Conflicts

When two packages produce the same `<category>/<model-name>/<component-name>` path:

1. First package wins (idempotent — same package always wins)
2. Second package's conflicting view is reported as a warning
3. No automatic resolution; user must rename or move one package
