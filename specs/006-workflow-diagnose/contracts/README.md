# Contracts: Workflow Diagnose CLI

## CLI Contract

```bash
comfygo workflow diagnose (--workflow PATH | --prompt-id ID | --latest-error) [--host URL] [--pretty]
```

### Flags

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--workflow` | one-of | — | Path to API-format workflow JSON |
| `--prompt-id` | one-of | — | Load workflow + execution from history |
| `--latest-error` | one-of | — | Newest error entry in recent history |
| `--host` | no | `http://127.0.0.1:8188` | ComfyUI base URL |
| `--pretty` | no | false | Indented JSON stdout |

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | No validation errors and no execution error (when execution section present) |
| 1 | Validation or execution errors found, or usage error |
| 2 | Server unreachable or history/workflow load failure |

### Stdout

Single JSON document matching `data-model.md` DiagnoseReport.

### Stderr

Progress hints and connectivity errors only; must not break JSON parsing of stdout.

## HTTP Contract (local ComfyUI)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/prompt` | Validate workflow; read `node_errors` |
| GET | `/object_info` | Installed node class types |
| GET | `/models/{folder}` | Model names per folder |
| GET | `/history` | List recent entries (`--latest-error`) |
| GET | `/history/{id}` | Single entry (`--prompt-id`) |

## Agent Protocol (AGENTS.md)

1. Run `comfygo workflow diagnose` with appropriate source flag.
2. Read `validation.node_errors` and `execution.errors` first.
3. Check `dependencies.missing_nodes` / `missing_models`.
4. Propose fixes as API JSON edits or `remediation[].command`.
5. Re-run diagnose until exit code 0 before asking user to queue in ComfyUI.
