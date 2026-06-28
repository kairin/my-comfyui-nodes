# Quickstart: Workflow Diagnose CLI

## Prerequisites

- ComfyUI running locally (e.g. via `comfygo go` or `comfygo launch`)
- `COMFYUI_DIR` configured via direnv or `.env.local`
- uv available

## Diagnose a workflow file

```bash
comfygo workflow diagnose --workflow /path/to/workflow_api.json
```

Expected: JSON on stdout with `validation` and `dependencies` sections.

## Diagnose a failed run

```bash
comfygo workflow diagnose --prompt-id <uuid-from-comfyui-history>
```

Or:

```bash
comfygo workflow diagnose --latest-error
```

Expected: JSON includes `execution` with error messages when the run failed.

## Agent workflow

1. User reports failure → agent runs `--latest-error` or `--prompt-id`.
2. Agent reads stdout JSON, proposes fixed workflow file or parameter changes.
3. User loads fixed JSON in ComfyUI (Load/drag-drop).
4. Agent re-runs `comfygo workflow diagnose --workflow fixed.json` until exit 0.

## Verification (CI)

```bash
uv run pytest custom_nodes/comfygo_model_registry/tests/test_workflow_diagnose.py -q
```

## Verification (live, optional)

With ComfyUI running and a known-broken fixture workflow:

```bash
comfygo workflow diagnose --workflow specs/006-workflow-diagnose/fixtures/invalid_vae.json
echo $?   # expect non-zero
```
