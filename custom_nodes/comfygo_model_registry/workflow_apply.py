"""Apply JSON patches to ComfyUI API workflows with filesystem checkpoints."""

from __future__ import annotations

import copy
import json
import pathlib
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from .workflow_diagnose import load_workflow_file

CHECKPOINT_DIRNAME = ".comfygo_debug/checkpoints"

SUPPORTED_OPS = frozenset({"set_input", "connect", "add_node", "remove_node"})


def checkpoint_root(base: pathlib.Path | None = None) -> pathlib.Path:
    root = base or pathlib.Path.cwd()
    return root / CHECKPOINT_DIRNAME


def _new_checkpoint_id() -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def save_checkpoint(
    workflow: dict[str, Any],
    *,
    source_path: str | None = None,
    label: str = "pre_apply",
    patches: list[dict[str, Any]] | None = None,
    base_dir: pathlib.Path | None = None,
) -> str:
    checkpoint_id = _new_checkpoint_id()
    dest = checkpoint_root(base_dir)
    dest.mkdir(parents=True, exist_ok=True)
    record = {
        "id": checkpoint_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "label": label,
        "source_path": source_path,
        "patches": patches,
        "workflow": workflow,
    }
    path = dest / f"{checkpoint_id}.json"
    path.write_text(json.dumps(record, indent=2, ensure_ascii=False), encoding="utf-8")
    return checkpoint_id


def list_checkpoints(base_dir: pathlib.Path | None = None) -> list[dict[str, Any]]:
    dest = checkpoint_root(base_dir)
    if not dest.is_dir():
        return []
    items: list[dict[str, Any]] = []
    for path in sorted(dest.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(record, dict):
            continue
        items.append(
            {
                "id": record.get("id", path.stem),
                "created_at": record.get("created_at"),
                "label": record.get("label"),
                "source_path": record.get("source_path"),
                "path": str(path),
            }
        )
    return items


def load_checkpoint(
    checkpoint_id: str, base_dir: pathlib.Path | None = None
) -> dict[str, Any]:
    dest = checkpoint_root(base_dir)
    path = dest / f"{checkpoint_id}.json"
    if not path.is_file():
        raise LookupError(f"Checkpoint not found: {checkpoint_id}")
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict) or "workflow" not in record:
        raise ValueError(f"Invalid checkpoint file: {checkpoint_id}")
    workflow = record["workflow"]
    if not isinstance(workflow, dict):
        raise ValueError(f"Invalid workflow in checkpoint: {checkpoint_id}")
    return record


def restore_checkpoint_to_file(
    checkpoint_id: str,
    output_path: pathlib.Path,
    *,
    base_dir: pathlib.Path | None = None,
) -> None:
    record = load_checkpoint(checkpoint_id, base_dir=base_dir)
    workflow = record["workflow"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(workflow, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def load_patches(path: pathlib.Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "patches" in data:
        data = data["patches"]
    if not isinstance(data, list):
        raise ValueError("Patch file must be a JSON array or {patches: [...]}")
    for i, patch in enumerate(data):
        if not isinstance(patch, dict):
            raise ValueError(f"Patch {i} must be an object")
        op = patch.get("op")
        if op not in SUPPORTED_OPS:
            raise ValueError(f"Unsupported patch op: {op!r}")
    return data


def _next_node_id(workflow: dict[str, Any]) -> str:
    numeric_ids = [int(k) for k in workflow if re.fullmatch(r"\d+", k)]
    return str(max(numeric_ids, default=0) + 1)


def _apply_set_input(workflow: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    node_id = str(patch["node"])
    if node_id not in workflow:
        raise KeyError(f"Node not found: {node_id}")
    inputs = workflow[node_id].setdefault("inputs", {})
    param = patch["input"]
    old = inputs.get(param)
    inputs[param] = patch["value"]
    return {
        "op": "set_input",
        "node": node_id,
        "input": param,
        "old_value": old,
        "new_value": patch["value"],
    }


def _apply_connect(workflow: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    to_node = str(patch["to"])
    if to_node not in workflow:
        raise KeyError(f"Target node not found: {to_node}")
    from_node = str(patch["from"])
    if from_node not in workflow:
        raise KeyError(f"Source node not found: {from_node}")
    slot = int(patch.get("slot", 0))
    param = patch["input"]
    inputs = workflow[to_node].setdefault("inputs", {})
    old = inputs.get(param)
    inputs[param] = [from_node, slot]
    return {
        "op": "connect",
        "to": to_node,
        "input": param,
        "from": from_node,
        "slot": slot,
        "old_value": old,
    }


def _apply_add_node(workflow: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    node_id = patch.get("node_id") or patch.get("node")
    if node_id is None or not str(node_id).strip():
        node_id = _next_node_id(workflow)
    node_id = str(node_id)
    if node_id in workflow:
        raise ValueError(f"Node id already exists: {node_id}")
    class_type = patch["class_type"]
    inputs = patch.get("inputs") or {}
    if not isinstance(inputs, dict):
        raise ValueError("add_node inputs must be an object")
    meta = patch.get("meta") or {"title": class_type}
    workflow[node_id] = {
        "class_type": class_type,
        "inputs": copy.deepcopy(inputs),
        "_meta": meta,
    }
    return {
        "op": "add_node",
        "node_id": node_id,
        "class_type": class_type,
        "inputs": inputs,
    }


def _apply_remove_node(
    workflow: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    node_id = str(patch.get("node") or patch.get("node_id"))
    if node_id not in workflow:
        raise KeyError(f"Node not found: {node_id}")
    removed = workflow.pop(node_id)
    cleared: list[dict[str, str]] = []
    for other_id, node in workflow.items():
        inputs = node.get("inputs") or {}
        for input_name, input_value in list(inputs.items()):
            if (
                isinstance(input_value, list)
                and len(input_value) == 2
                and str(input_value[0]) == node_id
            ):
                del inputs[input_name]
                cleared.append({"node": other_id, "input": input_name})
    return {
        "op": "remove_node",
        "node_id": node_id,
        "removed_class_type": removed.get("class_type"),
        "cleared_connections": cleared,
    }


def apply_patches(
    workflow: dict[str, Any],
    patches: list[dict[str, Any]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    wf = copy.deepcopy(workflow)
    applied: list[dict[str, Any]] = []
    for patch in patches:
        op = patch["op"]
        if op == "set_input":
            applied.append(_apply_set_input(wf, patch))
        elif op == "connect":
            applied.append(_apply_connect(wf, patch))
        elif op == "add_node":
            applied.append(_apply_add_node(wf, patch))
        elif op == "remove_node":
            applied.append(_apply_remove_node(wf, patch))
        else:
            raise ValueError(f"Unsupported op: {op}")
    return wf, applied


def default_output_path(workflow_path: pathlib.Path) -> pathlib.Path:
    return workflow_path.with_name(
        f"{workflow_path.stem}.applied{workflow_path.suffix}"
    )


def apply_workflow_file(
    workflow_path: pathlib.Path,
    patch_path: pathlib.Path,
    *,
    output_path: pathlib.Path | None = None,
    base_dir: pathlib.Path | None = None,
) -> dict[str, Any]:
    workflow = load_workflow_file(workflow_path)
    patches = load_patches(patch_path)
    checkpoint_id = save_checkpoint(
        workflow,
        source_path=str(workflow_path.resolve()),
        label="pre_apply",
        patches=patches,
        base_dir=base_dir,
    )
    patched, applied_log = apply_patches(workflow, patches)
    out = output_path or default_output_path(workflow_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(patched, indent=2, ensure_ascii=False), encoding="utf-8")
    return {
        "checkpoint_id": checkpoint_id,
        "input": str(workflow_path.resolve()),
        "output": str(out.resolve()),
        "applied": applied_log,
        "workflow": patched,
    }


def apply_result_exit_code(result: dict[str, Any]) -> int:
    validation = result.get("validation")
    if validation is not None and not validation.get("ok", True):
        return 1
    return 0
