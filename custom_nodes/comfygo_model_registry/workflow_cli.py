"""CLI entry: comfygo workflow (diagnose, apply, checkpoint)."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys

from .workflow_apply import (
    apply_result_exit_code,
    apply_workflow_file,
    list_checkpoints,
    restore_checkpoint_to_file,
)
from .workflow_diagnose import (
    DEFAULT_HOST,
    DiagnoseOptions,
    UrllibComfyClient,
    diagnose,
    report_exit_code,
    validate_workflow,
)


def _add_diagnose_parser(sub: argparse._SubParsersAction) -> None:
    diag = sub.add_parser(
        "diagnose",
        help="Validate workflow and emit structured JSON report",
    )
    source = diag.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--workflow", type=pathlib.Path, help="API-format workflow JSON file"
    )
    source.add_argument(
        "--prompt-id", type=str, help="Load workflow from ComfyUI history"
    )
    source.add_argument(
        "--latest-error",
        action="store_true",
        help="Diagnose the most recent error in ComfyUI history",
    )
    diag.add_argument("--host", type=str, default=DEFAULT_HOST, help="ComfyUI base URL")
    diag.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON to stdout"
    )


def _add_apply_parser(sub: argparse._SubParsersAction) -> None:
    apply_p = sub.add_parser("apply", help="Apply JSON patches to a workflow file")
    apply_p.add_argument(
        "--workflow", type=pathlib.Path, required=True, help="Input workflow JSON"
    )
    apply_p.add_argument(
        "--patch", type=pathlib.Path, required=True, help="Patch list JSON"
    )
    apply_p.add_argument(
        "--output",
        type=pathlib.Path,
        default=None,
        help="Output path (default: <stem>.applied.json)",
    )
    apply_p.add_argument(
        "--validate",
        action="store_true",
        help="Validate patched workflow against live ComfyUI",
    )
    apply_p.add_argument(
        "--host", type=str, default=DEFAULT_HOST, help="ComfyUI base URL"
    )
    apply_p.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON to stdout"
    )


def _add_checkpoint_parser(sub: argparse._SubParsersAction) -> None:
    ckpt = sub.add_parser("checkpoint", help="List or restore workflow checkpoints")
    ckpt_sub = ckpt.add_subparsers(dest="checkpoint_command", required=True)
    ckpt_sub.add_parser("list", help="List saved checkpoints")
    restore_p = ckpt_sub.add_parser("restore", help="Restore checkpoint to a file")
    restore_p.add_argument("--id", type=str, required=True, help="Checkpoint id")
    restore_p.add_argument(
        "--output", type=pathlib.Path, required=True, help="Output workflow JSON path"
    )
    restore_p.add_argument(
        "--pretty", action="store_true", help="Pretty-print JSON to stdout"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="comfygo workflow",
        description="Diagnose and patch ComfyUI API workflows for agent review.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    _add_diagnose_parser(sub)
    _add_apply_parser(sub)
    _add_checkpoint_parser(sub)
    return parser


def _emit_json(data: dict, pretty: bool) -> None:
    if pretty:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(data, ensure_ascii=False))


def _cmd_diagnose(args: argparse.Namespace) -> int:
    options = DiagnoseOptions(
        host=args.host,
        workflow_path=args.workflow,
        prompt_id=args.prompt_id,
        latest_error=args.latest_error,
    )
    try:
        client = UrllibComfyClient(host=options.host)
        report = diagnose(client, options)
    except (ConnectionError, LookupError, ValueError) as exc:
        print(f"workflow diagnose: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"workflow diagnose: {exc}", file=sys.stderr)
        return 2

    _emit_json(report, args.pretty)
    return report_exit_code(report)


def _cmd_apply(args: argparse.Namespace) -> int:
    try:
        result = apply_workflow_file(
            args.workflow,
            args.patch,
            output_path=args.output,
        )
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"workflow apply: {exc}", file=sys.stderr)
        return 2

    workflow = result.pop("workflow")
    if args.validate:
        try:
            client = UrllibComfyClient(host=args.host)
            validation = validate_workflow(client, workflow)
            result["validation"] = validation
        except ConnectionError as exc:
            print(f"workflow apply: validate failed: {exc}", file=sys.stderr)
            return 2

    _emit_json(result, args.pretty)
    return apply_result_exit_code(result)


def _cmd_checkpoint(args: argparse.Namespace) -> int:
    if args.checkpoint_command == "list":
        items = list_checkpoints()
        _emit_json({"checkpoints": items}, getattr(args, "pretty", False))
        return 0

    if args.checkpoint_command == "restore":
        try:
            restore_checkpoint_to_file(args.id, args.output)
        except (LookupError, ValueError, OSError) as exc:
            print(f"workflow checkpoint: {exc}", file=sys.stderr)
            return 2
        _emit_json(
            {
                "restored": True,
                "checkpoint_id": args.id,
                "output": str(args.output.resolve()),
            },
            args.pretty,
        )
        return 0

    print(
        f"workflow checkpoint: unknown command: {args.checkpoint_command}",
        file=sys.stderr,
    )
    return 2


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "diagnose":
        return _cmd_diagnose(args)
    if args.command == "apply":
        return _cmd_apply(args)
    if args.command == "checkpoint":
        return _cmd_checkpoint(args)

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
