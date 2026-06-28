# Research: Workflow Diagnose CLI

**Date**: 2026-06-28

## Decision: CLI-first agent observation (not in-browser Copilot)

**Rationale**: User stack is SSH + tmux + Cursor agent. Copilot's `graphToPrompt()` + canvas push requires a browser extension. A JSON report via `comfygo` matches existing doctor/models patterns.

**Alternatives considered**:
- Embed multi-agent OpenAI loop like ComfyUI-Copilot — rejected (API keys, scope, UI)
- Import Grok comfyui skill scripts as dependency — rejected (external path, duplicate maintenance)
- Filesystem-only model scan — rejected (ComfyUI server is authoritative for what runs)

## Decision: ComfyUI `/prompt` POST for validation

**Rationale**: Same path Copilot's `ComfyGateway.run_prompt` uses. Returns `node_errors` without requiring GPU execution when graph is invalid.

**Alternatives considered**:
- Import ComfyUI `execution` module in-process — rejected (requires ComfyUI Python env coupling)

## Decision: History for runtime failures

**Rationale**: `GET /history/{prompt_id}` includes status messages and embedded prompt. Avoids manual export after failed queue.

**Alternatives considered**:
- WebSocket-only monitoring — rejected (needs active subscription at failure time)

## Decision: stdlib HTTP only

**Rationale**: Matches repo hygiene (no new deps), sufficient for local single-host calls.

**Alternatives considered**:
- `requests` / `aiohttp` — rejected for v1 simplicity
