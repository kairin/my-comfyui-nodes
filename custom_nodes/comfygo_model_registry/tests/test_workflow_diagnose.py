"""Tests for workflow diagnose — mocked HTTP only."""

from __future__ import annotations

import json
import pathlib

import pytest

from custom_nodes.comfygo_model_registry import workflow_diagnose as wd


class FakeClient:
    def __init__(self, routes: dict[tuple[str, str], tuple[int, object]]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str, object | None]] = []

    def get(self, path: str) -> tuple[int, object]:
        self.calls.append(("GET", path, None))
        return self.routes.get(("GET", path), (404, {}))

    def post(self, path: str, body: dict) -> tuple[int, object]:
        self.calls.append(("POST", path, body))
        return self.routes.get(("POST", path), (200, {"prompt_id": "ok"}))


SAMPLE_WORKFLOW = {
    "1": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "missing.safetensors"},
    },
    "2": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "missing_ckpt.safetensors"},
    },
}


def test_load_workflow_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "wf.json"
    path.write_text(json.dumps(SAMPLE_WORKFLOW), encoding="utf-8")
    loaded = wd.load_workflow_file(path)
    assert loaded["1"]["class_type"] == "VAELoader"


def test_extract_workflow_from_history_list_prompt() -> None:
    entry = {"prompt": [1, "pid", SAMPLE_WORKFLOW, {}, []]}
    assert wd.extract_workflow_from_history(entry) == SAMPLE_WORKFLOW


def test_validate_workflow_node_errors() -> None:
    client = FakeClient(
        {
            ("POST", "/prompt"): (
                400,
                {
                    "node_errors": {
                        "1": {
                            "class_type": "VAELoader",
                            "errors": [{"message": "value not in list"}],
                        }
                    }
                },
            )
        }
    )
    result = wd.validate_workflow(client, SAMPLE_WORKFLOW)
    assert result["ok"] is False
    assert "1" in result["node_errors"]


def test_check_dependencies_missing_node_and_model() -> None:
    client = FakeClient(
        {
            ("GET", "/object_info"): (200, {"CheckpointLoaderSimple": {}}),
            ("GET", "/models/checkpoints"): (200, ["real.safetensors"]),
            ("GET", "/models/vae"): (200, ["ae.safetensors"]),
        }
    )
    deps = wd.check_dependencies(client, SAMPLE_WORKFLOW)
    assert any(n["class_type"] == "VAELoader" for n in deps["missing_nodes"])
    assert deps["missing_models"]
    assert deps["missing_models"][0]["parameter"] == "vae_name"


def test_diagnose_from_workflow_file(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "wf.json"
    path.write_text(json.dumps(SAMPLE_WORKFLOW), encoding="utf-8")
    client = FakeClient(
        {
            ("POST", "/prompt"): (
                400,
                {"node_errors": {"1": {"errors": [{"message": "bad vae"}]}}},
            ),
            ("GET", "/object_info"): (
                200,
                {"VAELoader": {}, "CheckpointLoaderSimple": {}},
            ),
            ("GET", "/models/vae"): (200, ["ae.safetensors"]),
            ("GET", "/models/checkpoints"): (200, ["real.safetensors"]),
        }
    )
    report = wd.diagnose(
        client,
        wd.DiagnoseOptions(workflow_path=path, host="http://127.0.0.1:8188"),
    )
    assert report["source"]["type"] == "workflow_file"
    assert report["validation"]["ok"] is False
    assert report["remediation"]
    assert wd.report_exit_code(report) == 1


def test_diagnose_from_prompt_id_with_execution_error() -> None:
    history_entry = {
        "prompt": [1, "abc-123", SAMPLE_WORKFLOW, {}, []],
        "status": {
            "status_str": "error",
            "completed": False,
            "messages": [
                [
                    "execution_error",
                    {"node_id": "1", "exception_message": "CUDA OOM"},
                ]
            ],
        },
    }
    client = FakeClient(
        {
            ("GET", "/history/abc-123"): (200, {"abc-123": history_entry}),
            ("POST", "/prompt"): (200, {}),
            ("GET", "/object_info"): (
                200,
                {"VAELoader": {}, "CheckpointLoaderSimple": {}},
            ),
            ("GET", "/models/vae"): (200, ["ae.safetensors"]),
            ("GET", "/models/checkpoints"): (200, ["real.safetensors"]),
        }
    )
    report = wd.diagnose(
        client,
        wd.DiagnoseOptions(prompt_id="abc-123", host="http://127.0.0.1:8188"),
    )
    assert report["source"]["type"] == "prompt_id"
    assert report["execution"]["status_str"] == "error"
    assert report["execution"]["errors"]
    assert any(h["kind"] == "execution_error" for h in report["remediation"])


def test_find_latest_error_prompt_id() -> None:
    client = FakeClient(
        {
            ("GET", "/history?max_items=64"): (
                200,
                {
                    "ok-1": {"status": {"status_str": "success"}},
                    "err-1": {"status": {"status_str": "error"}},
                    "err-2": {"status": {"status_str": "error"}},
                },
            )
        }
    )
    assert wd.find_latest_error_prompt_id(client) == "err-2"


def test_find_latest_error_raises_when_none() -> None:
    client = FakeClient(
        {("GET", "/history?max_items=64"): (200, {"ok": {"status": {}}})}
    )
    with pytest.raises(LookupError):
        wd.find_latest_error_prompt_id(client)


def test_diagnose_requires_single_source() -> None:
    client = FakeClient({})
    with pytest.raises(ValueError):
        wd.diagnose(client, wd.DiagnoseOptions())


def test_workflow_cli_main_success_exit_zero(
    tmp_path: pathlib.Path, capsys, monkeypatch
) -> None:
    from custom_nodes.comfygo_model_registry import workflow_cli

    path = tmp_path / "wf.json"
    path.write_text(
        json.dumps(
            {
                "1": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "real.safetensors"},
                }
            }
        ),
        encoding="utf-8",
    )

    class OkClient:
        def get(self, path: str) -> tuple[int, object]:
            if path == "/object_info":
                return 200, {"CheckpointLoaderSimple": {}}
            if path == "/models/checkpoints":
                return 200, ["real.safetensors"]
            return 404, {}

        def post(self, path: str, body: dict) -> tuple[int, object]:
            return 200, {"prompt_id": "x"}

    monkeypatch.setattr(workflow_cli, "UrllibComfyClient", lambda host: OkClient())

    code = workflow_cli.main(["diagnose", "--workflow", str(path)])

    assert code == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["validation"]["ok"] is True
