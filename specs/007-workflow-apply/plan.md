# Implementation Plan: Workflow Apply CLI

**Branch**: `007-workflow-apply` | **Date**: 2026-06-28 | **Spec**: [spec.md](spec.md)

## Summary

Extend `comfygo workflow` with `apply` and `checkpoint` subcommands. `workflow_apply.py` applies patch ops to API JSON, stores checkpoints under `.comfygo_debug/checkpoints/`, optionally validates via existing `workflow_diagnose` helpers.

## Technical Context

Python 3.11+ in `comfygo_model_registry`; Bash dispatch in `comfy-local`. Depends on 006 `workflow_diagnose` for load/normalize/validate.

## Constitution Check

PASS — uv-first, gitignored runtime checkpoints, no secrets, read-only server except validation POST.

## Structure

```text
custom_nodes/comfygo_model_registry/
├── workflow_apply.py       # patches + checkpoints
├── workflow_cli.py         # add apply + checkpoint subcommands
└── tests/test_workflow_apply.py

scripts/comfy-local         # dispatch apply, checkpoint
AGENTS.md                   # updated protocol
```
