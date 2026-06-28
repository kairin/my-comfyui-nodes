"""ComfyUI workflow diagnosis for agent review (read-only).

Validates API-format workflows against a running ComfyUI server, checks node and
model dependencies, and optionally merges execution errors from history.
"""

from __future__ import annotations

import json
import pathlib
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urljoin

DEFAULT_HOST = "http://127.0.0.1:8188"

MODEL_LOADERS: dict[str, list[tuple[str, str]]] = {
    "CheckpointLoaderSimple": [("ckpt_name", "checkpoints")],
    "CheckpointLoader": [("ckpt_name", "checkpoints")],
    "VAELoader": [("vae_name", "vae")],
    "LoraLoader": [("lora_name", "loras")],
    "CLIPLoader": [("clip_name", "clip")],
    "UNETLoader": [("unet_name", "unet")],
    "DualCLIPLoader": [("clip_name1", "clip"), ("clip_name2", "clip")],
}

FOLDER_ALIASES: dict[str, list[str]] = {
    "unet": ["unet", "diffusion_models"],
    "diffusion_models": ["diffusion_models", "unet"],
    "clip": ["clip", "text_encoders"],
    "text_encoders": ["text_encoders", "clip"],
}

NODE_TO_PACKAGE: dict[str, str] = {
    "VHS_VideoCombine": "comfyui-videohelpersuite",
    "VHS_LoadVideo": "comfyui-videohelpersuite",
    "UNETLoaderGGUF": "ComfyUI-GGUF",
    "DualCLIPLoaderGGUF": "ComfyUI-GGUF",
}


class ComfyHttpClient(Protocol):
    def get(self, path: str) -> tuple[int, Any]: ...

    def post(self, path: str, body: dict[str, Any]) -> tuple[int, Any]: ...


@dataclass
class UrllibComfyClient:
    host: str
    timeout: float = 30.0

    def _request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
    ) -> tuple[int, Any]:
        url = urljoin(self.host.rstrip("/") + "/", path.lstrip("/"))
        data = None
        headers = {"Accept": "application/json"}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # nosec B310
                status = resp.status
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            status = exc.code
            raw = exc.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as exc:
            raise ConnectionError(
                f"Cannot reach ComfyUI at {self.host}: {exc}"
            ) from exc
        if not raw:
            return status, None
        try:
            return status, json.loads(raw)
        except json.JSONDecodeError:
            return status, {"raw": raw[:500]}

    def get(self, path: str) -> tuple[int, Any]:
        return self._request("GET", path)

    def post(self, path: str, body: dict[str, Any]) -> tuple[int, Any]:
        return self._request("POST", path, body)


@dataclass
class DiagnoseOptions:
    host: str = DEFAULT_HOST
    workflow_path: pathlib.Path | None = None
    prompt_id: str | None = None
    latest_error: bool = False


def load_workflow_file(path: pathlib.Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError(f"Workflow file must be a JSON object: {path}")
    return normalize_workflow(data)


def _is_api_node_map(data: dict[str, Any]) -> bool:
    return all(isinstance(k, str) and isinstance(v, dict) for k, v in data.items())


def normalize_workflow(data: dict[str, Any]) -> dict[str, Any]:
    """Accept bare API prompt or wrapped {prompt: {...}}."""
    prompt = data.get("prompt")
    if isinstance(prompt, dict) and _is_api_node_map(prompt):
        return prompt
    if _is_api_node_map(data):
        return data
    raise ValueError("Unrecognized workflow JSON shape; expected API-format node map")


def extract_workflow_from_history(entry: dict[str, Any]) -> dict[str, Any] | None:
    prompt_field = entry.get("prompt")
    if isinstance(prompt_field, (list, tuple)) and len(prompt_field) >= 3:
        candidate = prompt_field[2]
        if isinstance(candidate, dict):
            return candidate
    if isinstance(prompt_field, dict):
        return prompt_field
    return None


def extract_execution_diagnostics(entry: dict[str, Any]) -> dict[str, Any]:
    status = entry.get("status") or {}
    diag: dict[str, Any] = {
        "status_str": status.get("status_str"),
        "completed": status.get("completed"),
        "messages": [],
        "errors": [],
    }
    messages = status.get("messages") or []
    for msg in messages:
        if isinstance(msg, list) and len(msg) >= 2:
            mtype, mdata = msg[0], msg[1]
            diag["messages"].append({"type": mtype, "data": mdata})
            if mtype == "execution_error":
                diag["errors"].append(mdata)
        else:
            diag["messages"].append(msg)
    return diag


def workflow_summary(workflow: dict[str, Any]) -> dict[str, Any]:
    class_types = sorted(
        {
            node.get("class_type", "unknown")
            for node in workflow.values()
            if isinstance(node, dict)
        }
    )
    return {"node_count": len(workflow), "class_types": class_types}


def validate_workflow(
    client: ComfyHttpClient, workflow: dict[str, Any]
) -> dict[str, Any]:
    status, body = client.post(
        "/prompt",
        {"prompt": workflow, "client_id": "comfygo_diagnose"},
    )
    result: dict[str, Any] = {
        "http_status": status,
        "ok": True,
        "node_errors": {},
        "error": None,
    }
    if not isinstance(body, dict):
        result["ok"] = False
        result["error"] = {"message": "non-JSON validation response", "body": body}
        return result
    node_errors = body.get("node_errors") or {}
    if node_errors:
        result["ok"] = False
        result["node_errors"] = node_errors
    if body.get("error"):
        result["ok"] = False
        result["error"] = body["error"]
    if status >= 400 and result["ok"]:
        result["ok"] = False
        result["error"] = body
    return result


def _folder_aliases(folder: str) -> list[str]:
    return FOLDER_ALIASES.get(folder, [folder])


def _model_name_from_item(item: Any) -> str | None:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        for key in ("name", "filename", "path"):
            val = item.get(key)
            if isinstance(val, str):
                return val
    return None


def _parse_model_list(payload: Any) -> set[str]:
    if isinstance(payload, list):
        names: set[str] = set()
        for item in payload:
            name = _model_name_from_item(item)
            if name:
                names.add(name)
        return names
    if isinstance(payload, dict):
        names = set()
        for key in ("models", "files", "items"):
            if key in payload:
                names.update(_parse_model_list(payload[key]))
        return names
    return set()


def _model_present(needed: str, installed: set[str]) -> bool:
    if not installed:
        return False
    variants = {needed, pathlib.Path(needed).name, pathlib.Path(needed).stem}
    installed_variants: set[str] = set()
    for inst in installed:
        installed_variants.add(inst)
        installed_variants.add(pathlib.Path(inst).name)
        installed_variants.add(pathlib.Path(inst).stem)
    return bool(variants & installed_variants)


def fetch_object_info(client: ComfyHttpClient) -> tuple[set[str] | None, str | None]:
    status, body = client.get("/object_info")
    if status == 200 and isinstance(body, dict):
        return set(body.keys()), None
    return None, f"object_info unavailable (HTTP {status})"


def fetch_models_for_folder(client: ComfyHttpClient, folder: str) -> set[str] | None:
    combined: set[str] = set()
    any_ok = False
    for alias in _folder_aliases(folder):
        status, body = client.get(f"/models/{alias}")
        if status == 200:
            combined.update(_parse_model_list(body))
            any_ok = True
    return combined if any_ok else None


def _required_class_types(workflow: dict[str, Any]) -> set[str]:
    return {
        node.get("class_type")
        for node in workflow.values()
        if isinstance(node, dict) and node.get("class_type")
    }


def _missing_node_entries(
    required_nodes: set[str], installed_nodes: set[str]
) -> list[dict[str, Any]]:
    missing_nodes: list[dict[str, Any]] = []
    for cls in sorted(required_nodes):
        if cls in installed_nodes:
            continue
        entry: dict[str, Any] = {"class_type": cls}
        pkg = NODE_TO_PACKAGE.get(cls)
        if pkg:
            entry["fix_command"] = f"comfy node install {pkg}"
        missing_nodes.append(entry)
    return missing_nodes


def _installed_models_for_folder(
    client: ComfyHttpClient,
    folder: str,
    model_cache: dict[str, set[str] | None],
) -> set[str] | None:
    if folder not in model_cache:
        model_cache[folder] = fetch_models_for_folder(client, folder)
    return model_cache[folder]


def _missing_models_for_node(
    client: ComfyHttpClient,
    node_id: str,
    node: dict[str, Any],
    model_cache: dict[str, set[str] | None],
) -> list[dict[str, Any]]:
    class_type = node.get("class_type")
    loader_params = MODEL_LOADERS.get(class_type or "")
    if not loader_params:
        return []
    inputs = node.get("inputs") or {}
    missing_models: list[dict[str, Any]] = []
    for param, folder in loader_params:
        value = inputs.get(param)
        if not isinstance(value, str) or not value.strip():
            continue
        installed = _installed_models_for_folder(client, folder, model_cache)
        if installed is None or _model_present(value, installed):
            continue
        missing_models.append(
            {
                "node_id": node_id,
                "class_type": class_type,
                "parameter": param,
                "folder": folder,
                "wanted": value,
                "sample_installed": sorted(installed)[:5],
            }
        )
    return missing_models


def _missing_model_entries(
    client: ComfyHttpClient,
    workflow: dict[str, Any],
    model_cache: dict[str, set[str] | None],
) -> list[dict[str, Any]]:
    missing_models: list[dict[str, Any]] = []
    for node_id, node in workflow.items():
        if not isinstance(node, dict):
            continue
        missing_models.extend(
            _missing_models_for_node(client, node_id, node, model_cache)
        )
    return missing_models


def check_dependencies(
    client: ComfyHttpClient,
    workflow: dict[str, Any],
) -> dict[str, Any]:
    installed_nodes, skip_reason = fetch_object_info(client)
    if installed_nodes is None:
        missing_nodes: list[dict[str, Any]] = []
        node_check_skipped = True
    else:
        missing_nodes = _missing_node_entries(
            _required_class_types(workflow), installed_nodes
        )
        node_check_skipped = False

    result: dict[str, Any] = {
        "missing_nodes": missing_nodes,
        "missing_models": _missing_model_entries(client, workflow, {}),
    }
    if node_check_skipped:
        result["skipped_reason"] = skip_reason
    return result


def _validation_hints(validation: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for node_id, err_block in (validation.get("node_errors") or {}).items():
        if not isinstance(err_block, dict):
            continue
        for err in err_block.get("errors") or []:
            if not isinstance(err, dict):
                continue
            hints.append(
                {
                    "kind": "validation_error",
                    "node_id": node_id,
                    "message": err.get("message") or str(err),
                    "details": err.get("details"),
                }
            )
    return hints


def _dependency_hints(dependencies: dict[str, Any]) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for node in dependencies.get("missing_nodes") or []:
        hints.append(
            {
                "kind": "install_node",
                "message": f"Missing custom node: {node.get('class_type')}",
                "command": node.get("fix_command"),
                "class_type": node.get("class_type"),
            }
        )
    for model in dependencies.get("missing_models") or []:
        hints.append(
            {
                "kind": "missing_model",
                "node_id": model.get("node_id"),
                "parameter": model.get("parameter"),
                "message": (
                    f"Model not found: {model.get('wanted')} "
                    f"({model.get('parameter')} on node {model.get('node_id')})"
                ),
            }
        )
    return hints


def _execution_hints(execution: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not execution or not execution.get("errors"):
        return []
    hints: list[dict[str, Any]] = []
    for err in execution["errors"]:
        hints.append(
            {
                "kind": "execution_error",
                "message": err.get("exception_message")
                if isinstance(err, dict)
                else str(err),
                "node_id": err.get("node_id") if isinstance(err, dict) else None,
            }
        )
    return hints


def build_remediation(
    validation: dict[str, Any],
    dependencies: dict[str, Any],
    execution: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    return (
        _validation_hints(validation)
        + _dependency_hints(dependencies)
        + _execution_hints(execution)
    )


def fetch_history_entry(client: ComfyHttpClient, prompt_id: str) -> dict[str, Any]:
    status, body = client.get(f"/history/{prompt_id}")
    if status != 200 or not isinstance(body, dict):
        raise LookupError(f"prompt_id not found or history unavailable: {prompt_id}")
    if prompt_id in body:
        return body[prompt_id]
    if "status" in body or "prompt" in body:
        return body
    raise LookupError(f"prompt_id not found in history: {prompt_id}")


def fetch_recent_history(
    client: ComfyHttpClient, max_items: int = 64
) -> dict[str, Any]:
    status, body = client.get(f"/history?max_items={max_items}")
    if status != 200 or not isinstance(body, dict):
        raise LookupError("Could not fetch ComfyUI history")
    return body


def find_latest_error_prompt_id(client: ComfyHttpClient) -> str:
    history = fetch_recent_history(client)
    error_ids: list[str] = []
    for prompt_id, entry in history.items():
        if not isinstance(entry, dict):
            continue
        status = entry.get("status") or {}
        if status.get("status_str") == "error":
            error_ids.append(prompt_id)
    if not error_ids:
        raise LookupError("No error entries found in recent ComfyUI history")
    return error_ids[-1]


def build_diagnose_report(
    *,
    source: dict[str, Any],
    workflow: dict[str, Any],
    validation: dict[str, Any],
    dependencies: dict[str, Any],
    execution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "source": source,
        "workflow_summary": workflow_summary(workflow),
        "validation": validation,
        "dependencies": dependencies,
        "execution": execution,
        "remediation": build_remediation(validation, dependencies, execution),
    }


def _resolve_prompt_id(
    client: ComfyHttpClient, options: DiagnoseOptions
) -> tuple[DiagnoseOptions, str | None]:
    if options.latest_error:
        prompt_id = find_latest_error_prompt_id(client)
        return (
            DiagnoseOptions(
                host=options.host,
                prompt_id=prompt_id,
                latest_error=True,
            ),
            prompt_id,
        )
    return options, options.prompt_id


def _workflow_from_history(
    client: ComfyHttpClient, options: DiagnoseOptions, prompt_id: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    entry = fetch_history_entry(client, prompt_id)
    workflow = extract_workflow_from_history(entry)
    if workflow is None:
        raise ValueError(f"Could not extract workflow from history entry: {prompt_id}")
    execution = extract_execution_diagnostics(entry)
    source = {
        "type": "latest_error" if options.latest_error else "prompt_id",
        "prompt_id": prompt_id,
        "host": options.host,
    }
    return workflow, source, execution


def diagnose(client: ComfyHttpClient, options: DiagnoseOptions) -> dict[str, Any]:
    modes = sum(
        [
            options.workflow_path is not None,
            options.prompt_id is not None,
            options.latest_error,
        ]
    )
    if modes != 1:
        raise ValueError(
            "Specify exactly one of workflow_path, prompt_id, or latest_error"
        )

    options, prompt_id = _resolve_prompt_id(client, options)
    if prompt_id:
        workflow, source, execution = _workflow_from_history(client, options, prompt_id)
    else:
        assert options.workflow_path is not None
        workflow = load_workflow_file(options.workflow_path)
        source = {
            "type": "workflow_file",
            "path": str(options.workflow_path),
            "host": options.host,
        }
        execution = None

    validation = validate_workflow(client, workflow)
    dependencies = check_dependencies(client, workflow)
    return build_diagnose_report(
        source=source,
        workflow=workflow,
        validation=validation,
        dependencies=dependencies,
        execution=execution,
    )


def report_exit_code(report: dict[str, Any]) -> int:
    validation = report.get("validation") or {}
    execution = report.get("execution") or {}
    if not validation.get("ok", True):
        return 1
    if execution.get("status_str") == "error" or execution.get("errors"):
        return 1
    if report.get("dependencies", {}).get("missing_nodes") or report.get(
        "dependencies", {}
    ).get("missing_models"):
        return 1
    return 0
