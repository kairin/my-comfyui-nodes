"""Tests for workflow apply and checkpoints."""

from __future__ import annotations

import json
import pathlib

import pytest

from custom_nodes.comfygo_model_registry import workflow_apply as wa


SAMPLE = {
    "1": {
        "class_type": "VAELoader",
        "inputs": {"vae_name": "bad.safetensors"},
    },
    "2": {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": "model.safetensors"},
    },
    "3": {
        "class_type": "KSampler",
        "inputs": {"seed": 1},
    },
}


def test_set_input_patch() -> None:
    patched, log = wa.apply_patches(
        SAMPLE,
        [
            {
                "op": "set_input",
                "node": "1",
                "input": "vae_name",
                "value": "ae.safetensors",
            }
        ],
    )
    assert patched["1"]["inputs"]["vae_name"] == "ae.safetensors"
    assert log[0]["op"] == "set_input"


def test_connect_patch() -> None:
    patched, log = wa.apply_patches(
        SAMPLE,
        [{"op": "connect", "to": "3", "input": "model", "from": "2", "slot": 0}],
    )
    assert patched["3"]["inputs"]["model"] == ["2", 0]
    assert log[0]["op"] == "connect"


def test_add_node_patch() -> None:
    patched, log = wa.apply_patches(
        SAMPLE,
        [
            {
                "op": "add_node",
                "class_type": "EmptyLatentImage",
                "inputs": {"width": 512, "height": 512, "batch_size": 1},
            }
        ],
    )
    new_id = log[0]["node_id"]
    assert new_id in patched
    assert patched[new_id]["class_type"] == "EmptyLatentImage"


def test_remove_node_clears_connections() -> None:
    wf = {
        "1": {"class_type": "A", "inputs": {}},
        "2": {"class_type": "B", "inputs": {"x": ["1", 0]}},
    }
    patched, log = wa.apply_patches(wf, [{"op": "remove_node", "node": "1"}])
    assert "1" not in patched
    assert "x" not in patched["2"]["inputs"]
    assert log[0]["cleared_connections"]


def test_checkpoint_round_trip(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    cid = wa.save_checkpoint(SAMPLE, source_path="/tmp/wf.json", label="pre_apply")
    listed = wa.list_checkpoints()
    assert any(item["id"] == cid for item in listed)
    out = tmp_path / "restored.json"
    wa.restore_checkpoint_to_file(cid, out)
    restored = json.loads(out.read_text(encoding="utf-8"))
    assert restored == SAMPLE


def test_apply_workflow_file(tmp_path: pathlib.Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    wf_path = tmp_path / "wf.json"
    wf_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(
        json.dumps(
            [
                {
                    "op": "set_input",
                    "node": "1",
                    "input": "vae_name",
                    "value": "fixed.safetensors",
                }
            ]
        ),
        encoding="utf-8",
    )
    result = wa.apply_workflow_file(
        wf_path, patch_path, output_path=tmp_path / "out.json"
    )
    out = json.loads((tmp_path / "out.json").read_text(encoding="utf-8"))
    assert out["1"]["inputs"]["vae_name"] == "fixed.safetensors"
    assert result["checkpoint_id"]
    assert wa.load_checkpoint(result["checkpoint_id"])["workflow"] == SAMPLE


def test_apply_invalid_patch_raises(tmp_path: pathlib.Path) -> None:
    wf_path = tmp_path / "wf.json"
    wf_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    patch_path = tmp_path / "bad.json"
    patch_path.write_text(json.dumps([{"op": "nope"}]), encoding="utf-8")
    with pytest.raises(ValueError):
        wa.apply_workflow_file(wf_path, patch_path)


def test_workflow_cli_apply(monkeypatch, tmp_path: pathlib.Path, capsys) -> None:
    from custom_nodes.comfygo_model_registry import workflow_cli

    monkeypatch.chdir(tmp_path)
    wf_path = tmp_path / "wf.json"
    wf_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
    patch_path = tmp_path / "patch.json"
    patch_path.write_text(
        json.dumps(
            [
                {
                    "op": "set_input",
                    "node": "1",
                    "input": "vae_name",
                    "value": "ok.safetensors",
                }
            ]
        ),
        encoding="utf-8",
    )
    code = workflow_cli.main(
        [
            "apply",
            "--workflow",
            str(wf_path),
            "--patch",
            str(patch_path),
            "--output",
            str(tmp_path / "fixed.json"),
        ]
    )
    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["checkpoint_id"]
    assert (tmp_path / "fixed.json").is_file()
