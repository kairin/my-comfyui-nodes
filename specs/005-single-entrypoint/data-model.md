# Data Model: Single Entrypoint CLI

## Entities

### SingleEntryPointCommand

The one command users are expected to remember and invoke for all normal daily operations.

| Field              | Type          | Description                                      | Required |
|--------------------|---------------|--------------------------------------------------|----------|
| `name`             | `str`         | Literal command name: `"comfygo"`                | always   |
| `subcommands`      | `list[str]`   | Exposed subcommands surfaced via `--help` (doctor, models, sync, start, restart, update, install, refresh-upstreams, runtime-envrc, patch-cli, patch-comfyui, etc.) | always (may grow) |
| `dispatch`         | `str`         | Internal implementation: thin `scripts/comfygo` bash wrapper → `scripts/comfy-local "$@"` (or "go" when no args) | always |
| `path_setup`       | `str`         | How it enters PATH: repo `.envrc` prepends `scripts/` (when direnv allowed); fallback `.env.local` handling inside wrappers | always |

**Validation rules** (from FRs + clarifications):
- `name` is the single string users must be able to recall after one exposure in docs or constitution.
- All primary user flows (launch, diagnostics, enrichment, sync, patching) are reachable as `comfygo` or `comfygo <subcommand>`.
- Direct internal scripts remain executable for compatibility but are never the documented starting point for daily use.

### DocumentationSurface

Any artifact whose primary audience is end-users or daily operators (as opposed to feature implementers or AI agents).

| Field         | Type     | Description | Required |
|---------------|----------|-------------|----------|
| `path`        | `Path`   | Filesystem location (relative) e.g. `README.md`, `docs/workflow.md`, `docs/model-library.md` | always |
| `kind`        | `enum`   | `readme`, `workflow`, `model_library`, `quickstart_user`, `constitution`, `issue_template_user` | always |
| `must_lead_with_comfygo` | `bool` | True for sections describing normal daily operation | per kind |
| `allowed_bypass_sections` | `list[str]` | Headings under which direct `scripts/...` paths are tolerated (e.g. "Quality Gates", "For Contributors", "Bootstrap before direnv") | always |

**Validation rules**:
- In sections not listed in `allowed_bypass_sections`, every runnable example for daily tasks must start with the token `comfygo` (optionally with subcommand) as the first command on the line.
- `scripts/hf-select-download` examples must be rewritten to `comfygo models enrich` (the enrichment subcommand forwards to the same implementation).
- Historical specs/* quickstarts and contracts may continue to show the precise harness commands used by tests (they are not user-facing per this feature's scope).

### InternalWrapper

Implementation detail that must not be taught as the primary interface.

| Field     | Type   | Description | Required |
|-----------|--------|-------------|----------|
| `path`    | `Path` | e.g. `scripts/comfy-local`, `scripts/hf-select-download`, `scripts/update-from-upstreams.sh`, `scripts/install-to-comfyui.sh`, `scripts/comfy-*-with-local-nodes.sh`, `scripts/apply-*-patches.sh` | always |
| `status`  | `enum` | `supported_for_dev`, `deprecated_in_user_docs`, `bootstrap_only` | always |

**Relationships**:
- `SingleEntryPointCommand` delegates to one or more `InternalWrapper`s.
- `DocumentationSurface` references `SingleEntryPointCommand` for normal flows and may reference `InternalWrapper` only inside allowed bypass sections.
- Constitution text (a special DocumentationSurface) names the `SingleEntryPointCommand` under Safe Daily Operation and explicitly calls out the de-emphasis of wrappers.

## State Transitions (docs / governance)

- Before feature: mixed examples (some `comfygo`, many direct scripts in tutorials).
- After feature: 100% of user-tutorial flows (SC-002) start with `comfygo`; constitution reinforced; internal wrappers documented as "still work but not the thing to remember".
- No runtime state change (the facade already existed).

## Invariants
- No new public API surface is invented; the subcommand list is the one already implemented and described in `comfy-local` usage().
- Secret safety, uv-first, and vendored-source rules are orthogonal and already satisfied by the dispatch.
