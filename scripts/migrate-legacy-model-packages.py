#!/usr/bin/env python3
"""Move legacy category-folder weights into descriptor-first package folders.

Dry-run by default. Use --apply to move files and write comfygo-model.json,
then run reconcile when requested.

Targets the configured ComfyUI model root (COMFY_MODELS_DIR or COMFYUI_DIR/../models).
"""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Any


SCHEMA = "comfygo.model.v1"


@dataclass
class ComponentSpec:
    logical_name: str
    path: str
    categories: list[str]


@dataclass
class PackageSpec:
    name: str
    kind: str
    components: list[ComponentSpec]
    moves: list[tuple[str, str]] = field(default_factory=list)
    move_dir: tuple[str, str] | None = None
    notes: str | None = None


def _descriptor(pkg: PackageSpec) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "name": pkg.name,
        "kind": pkg.kind,
        "source": {"type": "local", "repo": "legacy-category-migration"},
        "components": {
            c.logical_name: {
                "path": c.path,
                "comfy_categories": c.categories,
            }
            for c in pkg.components
        },
        **({"notes": pkg.notes} if pkg.notes else {}),
    }


def _build_specs() -> list[PackageSpec]:
    loras = [
        (
            "Qwen-Image-2512-Lightning-4steps-V1.0-fp32",
            "Qwen-Image-2512-Lightning-4steps-V1.0-fp32.safetensors",
        ),
        (
            "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16",
            "Qwen-Image-Edit-2509-Lightning-4steps-V1.0-bf16.safetensors",
        ),
        (
            "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16",
            "Wuli-Qwen-Image-2512-Turbo-LoRA-2steps-V1.0-bf16.safetensors",
        ),
    ]
    specs: list[PackageSpec] = []
    for pkg_name, weight in loras:
        meta = weight.replace(".safetensors", ".metadata.json")
        specs.append(
            PackageSpec(
                name=pkg_name,
                kind="lora",
                components=[
                    ComponentSpec("lora", weight, ["loras"]),
                ],
                moves=[
                    (f"loras/{weight}", weight),
                    (f"loras/{meta}", meta),
                ],
                notes="Migrated from models/loras/",
            )
        )

    specs.append(
        PackageSpec(
            name="Anything2Real",
            kind="lora",
            components=[
                ComponentSpec(
                    "anything2real_2601", "anything2real_2601.safetensors", ["loras"]
                ),
                ComponentSpec(
                    "anything2real_2601_A_final_patched",
                    "anything2real_2601_A_final_patched.safetensors",
                    ["loras"],
                ),
                ComponentSpec(
                    "f2k_anything2real", "f2k_anything2real.safetensors", ["loras"]
                ),
                ComponentSpec(
                    "f2k_anything2real_a", "f2k_anything2real_a.safetensors", ["loras"]
                ),
            ],
            move_dir=("loras/Anything2Real", "Anything2Real"),
            notes="Migrated from models/loras/Anything2Real/",
        )
    )

    diffusion = [
        ("qwen-image-edit-2511-Q4_K_M", "qwen-image-edit-2511-Q4_K_M.gguf", "gguf"),
        (
            "qwen_image_2512_fp8_e4m3fn",
            "qwen_image_2512_fp8_e4m3fn.safetensors",
            "other",
        ),
        (
            "qwen_image_edit_2509_fp8_e4m3fn",
            "qwen_image_edit_2509_fp8_e4m3fn.safetensors",
            "other",
        ),
    ]
    for pkg_name, weight, kind in diffusion:
        meta = weight.rsplit(".", 1)[0] + ".metadata.json"
        specs.append(
            PackageSpec(
                name=pkg_name,
                kind=kind,
                components=[
                    ComponentSpec("weights", weight, ["diffusion_models"]),
                ],
                moves=[
                    (f"diffusion_models/{weight}", weight),
                    (f"diffusion_models/{meta}", meta),
                ],
                notes="Migrated from models/diffusion_models/",
            )
        )

    for pkg_name, weight in [
        ("e2e-qwen_image_vae", "e2e-qwen_image_vae.safetensors"),
        ("qwen_image_vae", "qwen_image_vae.safetensors"),
    ]:
        specs.append(
            PackageSpec(
                name=pkg_name,
                kind="vae",
                components=[ComponentSpec("vae", weight, ["vae"])],
                moves=[(f"vae/{weight}", weight)],
                notes="Migrated from models/vae/",
            )
        )

    specs.append(
        PackageSpec(
            name="qwen_2.5_vl_7b_fp8_scaled",
            kind="text_encoder",
            components=[
                ComponentSpec(
                    "text_encoder",
                    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    ["text_encoders"],
                ),
            ],
            moves=[
                (
                    "text_encoders/qwen_2.5_vl_7b_fp8_scaled.safetensors",
                    "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                ),
            ],
            notes="Migrated from models/text_encoders/",
        )
    )

    for folder, kind in [
        ("Qwen2.5-7B-Instruct-unbias-4bit", "text_encoder"),
        ("Z-Image-Engineer-V6", "text_encoder"),
    ]:
        specs.append(
            PackageSpec(
                name=folder,
                kind=kind,
                components=[ComponentSpec("model", ".", ["text_encoders"])],
                move_dir=(f"text_encoders/{folder}", folder),
                notes=f"Migrated from models/text_encoders/{folder}/",
            )
        )

    for folder in [
        "Qwen-Image-ControlNet-Union",
        "Qwen-Image-ControlNet-Inpainting",
    ]:
        specs.append(
            PackageSpec(
                name=folder,
                kind="controlnet",
                components=[
                    ComponentSpec(
                        "controlnet",
                        "diffusion_pytorch_model.safetensors",
                        ["controlnet"],
                    )
                ],
                move_dir=(f"controlnet/{folder}", folder),
                notes=f"Migrated from models/controlnet/{folder}/",
            )
        )

    return specs


def resolve_models_dir(explicit: str | None) -> pathlib.Path:
    if explicit:
        return pathlib.Path(explicit).resolve()
    import os

    env = os.environ.get("COMFY_MODELS_DIR")
    if env:
        return pathlib.Path(env).resolve()
    comfy = os.environ.get("COMFYUI_DIR")
    if comfy:
        sibling = pathlib.Path(comfy).resolve().parent / "models"
        if sibling.is_dir():
            return sibling
        inner = pathlib.Path(comfy).resolve() / "models"
        if inner.is_dir():
            return inner.resolve()
    raise SystemExit("Set --models-dir or COMFY_MODELS_DIR / COMFYUI_DIR")


def migrate_one(
    root: pathlib.Path,
    pkg: PackageSpec,
    *,
    apply: bool,
) -> list[str]:
    lines: list[str] = []
    dest = root / pkg.name
    if dest.exists() and not apply:
        lines.append(f"  exists: {dest} (would skip or merge)")
    if (
        dest.exists()
        and apply
        and not (pkg.move_dir and dest.samefile(root / pkg.move_dir[1]))
    ):
        raise SystemExit(f"Refusing to overwrite existing package dir: {dest}")

    if pkg.move_dir:
        src = root / pkg.move_dir[0]
        if not src.is_dir():
            lines.append(f"  skip: missing dir {src}")
            return lines
        lines.append(f"  move_dir: {src} -> {dest}")
        if apply:
            dest.parent.mkdir(parents=True, exist_ok=True)
            if dest.exists():
                raise SystemExit(f"Destination already exists: {dest}")
            shutil.move(str(src), str(dest))
    else:
        if apply:
            dest.mkdir(parents=True, exist_ok=True)
        for rel_src, rel_dest in pkg.moves:
            src = root / rel_src
            target = dest / rel_dest
            if not src.is_file():
                lines.append(f"  skip missing: {src}")
                continue
            lines.append(f"  move: {src} -> {target}")
            if apply:
                target.parent.mkdir(parents=True, exist_ok=True)
                if target.exists():
                    raise SystemExit(f"Refusing to overwrite {target}")
                shutil.move(str(src), str(target))

    desc_path = dest / "comfygo-model.json"
    lines.append(f"  write: {desc_path}")
    if apply:
        for comp in pkg.components:
            if comp.path != ".":
                if not (dest / comp.path).exists():
                    raise SystemExit(
                        f"Missing component path after move: {dest / comp.path}"
                    )
        desc_path.write_text(
            json.dumps(_descriptor(pkg), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-dir", type=str, default=None)
    parser.add_argument(
        "--apply", action="store_true", help="Perform moves and write descriptors"
    )
    parser.add_argument(
        "--reconcile",
        action="store_true",
        help="Run comfygo models reconcile --apply after migration",
    )
    args = parser.parse_args()

    root = resolve_models_dir(args.models_dir)
    specs = _build_specs()
    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"{mode}: migrate legacy weights under {root}")
    print(f"Packages planned: {len(specs)}\n")

    for pkg in specs:
        print(f"[{pkg.name}] kind={pkg.kind}")
        for line in migrate_one(root, pkg, apply=args.apply):
            print(line)
        print()

    if not args.apply:
        print("Dry-run complete. Re-run with --apply to migrate.")
        return 0

    if args.reconcile:
        repo = pathlib.Path(__file__).resolve().parent.parent
        script = repo / "scripts" / "comfygo-models.sh"
        print("Running reconcile --apply ...")
        subprocess.run(
            [str(script), "reconcile", "--apply"],
            check=True,
            cwd=str(repo),
        )

    print("Migration apply complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
