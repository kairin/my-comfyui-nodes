#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class CliError(Exception):
    pass


_SAFE_NAME_RE = re.compile(r"[^A-Za-z0-9_.+-]")
_BEARER_HEADER_RE = re.compile(r"(?i)(authorization:\s*)bearer\s+[A-Za-z0-9_./+-]+")


def _human_size(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    for unit in units:
        if size < 1024.0 or unit == units[-1]:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} B"


def _normalize_hf_repo(value: str) -> str:
    value = value.strip()
    if not value:
        return value

    if "://" not in value:
        return value

    try:
        parsed = urllib.parse.urlparse(value)
    except Exception:
        return value

    host = (parsed.hostname or "").lower()
    if host and not host.endswith("huggingface.co"):
        return value

    path = parsed.path.strip("/")
    if not path:
        return value

    parts = [segment for segment in path.split("/") if segment]
    if not parts:
        return value

    for prefix in ("api", "models", "spaces", "datasets"):
        if parts and parts[0] == prefix:
            parts = parts[1:]
            break

    if len(parts) < 2:
        return value

    return "/".join(parts[:2])


def _redact_token(value: str, token: str) -> str:
    if not value:
        return ""
    redacted = value
    if token:
        redacted = redacted.replace(token, "[REDACTED_TOKEN]")
    return _BEARER_HEADER_RE.sub(r"\1Bearer [REDACTED_TOKEN]", redacted)


def _resolve_directory_arg(value: str) -> Optional[Path]:
    if not value:
        return None

    candidate = Path(value).expanduser()
    try:
        if candidate.exists() and candidate.is_dir():
            return candidate.resolve()
    except OSError:
        return None
    return None


def _prompt_repo() -> Optional[str]:
    if not sys.stdin.isatty():
        return None
    try:
        value = input(
            "Please input url or repo (e.g. https://huggingface.co/user/repo or user/repo): "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not value:
        return None
    return _normalize_hf_repo(value)


def _read_token() -> str:
    token = os.getenv("HF_TOKEN", "").strip()
    if token:
        return token

    candidates = [
        Path.home() / ".hf.co" / "hf.token",
        Path.home() / ".huggingface" / "token",
    ]
    for path in candidates:
        try:
            return path.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            continue
        except Exception:
            continue

    return ""


def _fetch_civitai(model_name: str, token: str) -> Optional[Dict[str, Any]]:
    if not token or not model_name:
        return None
    query = urllib.parse.quote(model_name)
    url = f"https://civitai.com/api/v1/models?query={query}&limit=1"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
            if data.get("items"):
                item = data["items"][0]
                return {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "type": item.get("type"),
                    "nsfw": item.get("nsfw"),
                    "description": item.get("description"),
                }
    except Exception as e:
        print(f"Civitai query failed for {model_name}: {e}")
    return None


def _hf_env(token: str) -> Dict[str, str]:
    env = os.environ.copy()
    if token:
        env["HF_TOKEN"] = token
    return env


def _build_hf_request(url: str, token: str, start: int = 0) -> urllib.request.Request:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if start > 0:
        headers["Range"] = f"bytes={start}-"
    return urllib.request.Request(url, headers=headers)


def _resolve_models_root(models_root: Optional[str]) -> Optional[Path]:
    if models_root:
        return Path(models_root).expanduser().resolve()

    env_root = os.getenv("COMFYUI_MODELS_DIR", "").strip()
    if env_root:
        return Path(env_root).expanduser().resolve()

    comfy_ui_dir = os.getenv("COMFYUI_DIR", "").strip()
    if comfy_ui_dir:
        return (Path(comfy_ui_dir) / "models").expanduser().resolve()

    return None


def _sanitize_path_segment(value: str) -> str:
    value = value.strip().strip(". ")
    value = _SAFE_NAME_RE.sub("-", value)
    value = re.sub(r"-+", "-", value).strip("-._")
    return value or "model"


def _default_package_name(repo: str, revision: str) -> str:
    base = repo.strip().split("/")[-1]
    if not base:
        base = "model"
    base = _sanitize_path_segment(base)
    if revision and revision not in {"main", "master"}:
        rev = _sanitize_path_segment(revision)
        if rev and rev != "main":
            base = f"{base}-{rev}"
    return base


def _split_args_file_patterns(
    raw_patterns: Optional[List[str]],
) -> Dict[str, List[str]]:
    patterns: Dict[str, List[str]] = {}
    if not raw_patterns:
        return patterns

    for raw in raw_patterns:
        value = raw.strip()
        if ":" not in value:
            raise CliError(
                f"Invalid --category-mapping value '{raw}'. Expected format path:cat1,cat2"
            )
        pattern, categories = value.split(":", 1)
        pattern = pattern.strip()
        category_values = [cat.strip() for cat in categories.split(",") if cat.strip()]
        if not pattern or not category_values:
            raise CliError(
                f"Invalid --category-mapping value '{raw}'. Both path and categories are required"
            )

        normalized: List[str] = []
        for cat in category_values:
            if (
                "/" in cat
                or "\\" in cat
                or cat.startswith(".")
                or ".." in cat.split(".")
            ):
                raise CliError(f"Unsafe category name '{cat}'")
            normalized.append(cat)
        patterns[pattern] = normalized

    return patterns


def _infer_categories(file_path: str, overrides: Dict[str, List[str]]) -> List[str]:
    for pattern, categories in overrides.items():
        if fnmatch.fnmatch(file_path, pattern):
            return list(categories)

    lower = file_path.lower()
    lower_parts = lower.split("/")

    if any("transformer" in p for p in lower_parts):
        return ["diffusion_models"]
    if any("text_encoder" in p for p in lower_parts) or "textencoder" in lower:
        return ["text_encoders"]
    if "mmproj" in lower:
        return ["text_encoders"]
    if any("vae" == p or p.startswith("vae") for p in lower_parts):
        return ["vae"]
    if "lora" in lower:
        return ["loras"]
    if lower.endswith(".gguf"):
        return ["checkpoints"]
    if lower.endswith((".safetensors", ".sft", ".ckpt", ".bin", ".pt", ".pth")):
        return ["checkpoints"]

    return ["checkpoints"]


def _infer_kind(files: List[str], kind_override: Optional[str]) -> str:
    if kind_override:
        return kind_override

    names = [path.lower() for path in files]
    if any("transformer" in n or "diffusers" in n for n in names):
        return "diffusers"
    if any("lora" in n for n in names):
        return "lora"
    if any("embedding" in n for n in names):
        return "embedding"
    if any("vae" in n for n in names):
        return "vae"
    if any("text_encoder" in n or "textencoder" in n for n in names):
        return "text_encoder"
    if any("mmproj" in n for n in names):
        return "other"
    if any(n.endswith(".gguf") for n in names):
        return "gguf"
    if any(
        n.endswith((".safetensors", ".ckpt", ".bin", ".pt", ".pth", ".sft"))
        for n in names
    ):
        return "checkpoint"
    return "other"


def _safe_component_name(file_path: str) -> str:
    path = Path(file_path)
    if path.parent != Path("."):
        name = path.parent.name
    else:
        name = path.name.rsplit(".", 1)[0]
    name = _sanitize_path_segment(name)
    return name or "component"


def _local_file_status(
    output_dir: Path, file_path: str, remote_size: int
) -> Tuple[str, int]:
    local_path = output_dir / file_path
    if not local_path.exists():
        return "missing", 0

    try:
        local_size = local_path.stat().st_size
    except OSError:
        return "missing", 0

    if remote_size <= 0:
        return "unknown", local_size

    if local_size == remote_size:
        return "complete", local_size
    if local_size > remote_size:
        return "oversized", local_size
    return "partial", local_size


def _status_text(status: str, local_size: int, remote_size: int) -> str:
    if status == "complete":
        return "complete"
    if status == "missing":
        return "missing"
    if status == "oversized":
        return "oversized"
    if status == "partial":
        if remote_size <= 0:
            return "partial"
        return f"partial {_human_size(local_size)} / {_human_size(remote_size)}"
    return "unknown"


def _enrich_with_local_state(
    rows: List[Dict[str, Any]],
    output_dir: Path,
) -> List[Dict[str, Any]]:
    enriched = []
    for entry in rows:
        remote_size = int(entry.get("size", 0))
        status, local_size = _local_file_status(output_dir, entry["name"], remote_size)
        row = dict(entry)
        row["local_size"] = local_size
        row["local_status"] = status
        enriched.append(row)
    return enriched


def _to_output_location(
    repo: str,
    revision: str,
    output_dir: Optional[str],
    models_root: Optional[str],
    package_name: Optional[str],
) -> tuple[Path, bool, str]:
    if output_dir:
        return Path(output_dir).expanduser().resolve(), False, Path(output_dir).name

    root = _resolve_models_root(models_root)
    if root is None:
        # Fallback to current behavior if no known model root is configured.
        fallback = Path(".").resolve()
        return fallback, False, fallback.name

    name = _default_package_name(repo, revision)
    if package_name:
        name = _sanitize_path_segment(package_name)

    package_path = (root / name).resolve()
    return package_path, True, name


def _read_json_file(path: Path, *, description: str) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CliError(f"Missing {description}: {path}") from exc
    except json.JSONDecodeError as exc:
        raise CliError(f"Invalid JSON in {description} at {path}") from exc

    if not isinstance(data, dict):
        raise CliError(f"Unexpected format in {description} at {path}")

    return data


def _read_package_state(
    package_dir: Path,
) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return inferred (repo, revision, package_name) from local package metadata."""
    package_dir = package_dir.resolve()

    metadata_path = package_dir / ".comfygo-download.json"
    if metadata_path.exists():
        data = _read_json_file(metadata_path, description="download metadata")
        source = data.get("source", {})
        repo = source.get("repo") if isinstance(source, dict) else None
        revision = source.get("revision") if isinstance(source, dict) else None
        package_name = None
        if isinstance(data.get("package"), dict):
            package_name = data["package"].get("name")
            if isinstance(package_name, str):
                package_name = package_name.strip() or None
        return (
            repo.strip() if isinstance(repo, str) and repo.strip() else None,
            revision.strip()
            if isinstance(revision, str) and revision.strip()
            else None,
            package_name,
        )

    descriptor_path = package_dir / "comfygo-model.json"
    if descriptor_path.exists():
        data = _read_json_file(descriptor_path, description="model descriptor")
        source = data.get("source", {})
        repo = source.get("repo") if isinstance(source, dict) else None
        revision = source.get("version") if isinstance(source, dict) else None
        package_name = data.get("name")
        return (
            repo.strip() if isinstance(repo, str) and repo.strip() else None,
            revision.strip()
            if isinstance(revision, str) and revision.strip()
            else None,
            package_name.strip()
            if isinstance(package_name, str) and package_name.strip()
            else None,
        )

    return None, None, None


def _fetch_hf_tree(
    repo: str, revision: str, token: str, recursive: bool
) -> List[Dict[str, Any]]:
    endpoint = (
        f"https://huggingface.co/api/models/{urllib.parse.quote(repo, safe='/')}/tree/"
        f"{urllib.parse.quote(revision, safe='')}"
    )
    query = "?recursive=true" if recursive else ""
    request = _build_hf_request(f"{endpoint}{query}", token)
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read().decode("utf-8")
            data = json.loads(payload)
    except urllib.error.HTTPError as exc:
        raise CliError(
            _redact_token(
                f"HF API request failed: HTTP {exc.code} {exc.reason}",
                token,
            )
        ) from exc
    except urllib.error.URLError as exc:
        raise CliError(
            _redact_token(f"HF API request failed: {exc.reason}", token)
        ) from exc
    except json.JSONDecodeError as exc:
        raise CliError(
            _redact_token(f"HF API returned invalid JSON: {exc}", token)
        ) from exc

    if not isinstance(data, list):
        raise CliError("HF API returned an unexpected response for repository tree")

    return [
        entry
        for entry in data
        if isinstance(entry, dict) and entry.get("type") == "file"
    ]


def _extract_file_size(file_entry: Dict[str, Any]) -> int:
    size = file_entry.get("size")
    if not isinstance(size, int):
        size = 0

    lfs = file_entry.get("lfs")
    if isinstance(lfs, dict):
        lfs_size = lfs.get("size")
        if isinstance(lfs_size, int) and lfs_size > 0:
            size = lfs_size

    return size


def _filter_files(
    files: List[Dict[str, Any]],
    includes: Optional[List[str]],
    excludes: Optional[List[str]],
) -> List[Dict[str, Any]]:
    result = []
    for file_entry in files:
        path = file_entry.get("path")
        if not isinstance(path, str) or not path:
            continue

        include_hit = True
        if includes:
            include_hit = any(fnmatch.fnmatch(path, pattern) for pattern in includes)
        exclude_hit = False
        if excludes:
            exclude_hit = any(fnmatch.fnmatch(path, pattern) for pattern in excludes)

        if include_hit and not exclude_hit:
            result.append(file_entry)
    return result


def _resolve_selection(text: str, max_index: int) -> List[int]:
    text = (text or "").strip().lower()
    if text in ("", "a", "all"):
        return list(range(1, max_index + 1))
    if text in ("q", "quit", "none", "n", "no"):
        return []

    indices = set()
    for raw in text.split(","):
        part = raw.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start_s, end_s = part.split("-", 1)
                start = int(start_s.strip())
                end = int(end_s.strip())
            except ValueError as exc:
                raise CliError(f"Invalid range selection: {part}") from exc
            if start > end:
                start, end = end, start
            for idx in range(start, end + 1):
                if 1 <= idx <= max_index:
                    indices.add(idx)
            continue
        try:
            idx = int(part)
        except ValueError as exc:
            raise CliError(f"Invalid selection value: {part}") from exc
        if 1 <= idx <= max_index:
            indices.add(idx)
    return sorted(indices)


def _run_hf_dry_run(
    repo: str, file_path: str, revision: str, output_dir: Path, token: str
) -> None:
    command = [
        "hf",
        "download",
        repo,
        file_path,
        "--local-dir",
        str(output_dir),
        "--dry-run",
    ]
    if revision != "main":
        command.extend(["--revision", revision])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
        env=_hf_env(token),
    )
    if result.returncode != 0:
        raw_error = result.stderr.strip() or result.stdout.strip()
        error = _redact_token(raw_error, token)
        raise CliError(f"hf dry-run failed for {file_path}: {error}")


def _download_with_urllib(
    repo: str,
    revision: str,
    file_path: str,
    remote_size: int,
    output_dir: Path,
    token: str,
) -> int:
    dest = output_dir / file_path
    dest.parent.mkdir(parents=True, exist_ok=True)

    existing = dest.stat().st_size if dest.exists() else 0
    if existing == remote_size and remote_size > 0:
        print(f"skip: {file_path} already complete")
        return existing
    if existing > remote_size and remote_size > 0:
        print(f"warning: local file is larger than remote for {file_path}, restarting")
        dest.unlink(missing_ok=True)
        existing = 0

    resolved_repo = urllib.parse.quote(repo, safe="/")
    resolved_file = urllib.parse.quote(file_path, safe="/")
    url = f"https://huggingface.co/{resolved_repo}/resolve/{revision}/{resolved_file}?download=1"

    start = existing
    for attempt in range(1, 4):
        request = _build_hf_request(url, token=token, start=start)
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                status = getattr(response, "status", response.getcode())
                if start > 0 and status == 200:
                    dest.unlink(missing_ok=True)
                    start = 0
                    continue

                mode = "ab" if start > 0 and status == 206 else "wb"
                with dest.open(mode) as stream:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        stream.write(chunk)
        except urllib.error.HTTPError as exc:
            if start > 0 and exc.code == 416:
                dest.unlink(missing_ok=True)
                start = 0
                continue
            if exc.code in (408, 429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(min(attempt, 3))
                continue
            raise CliError(
                _redact_token(
                    f"hf download failed for {file_path}: HTTP {exc.code} {exc.reason}",
                    token,
                )
            ) from exc
        except urllib.error.URLError as exc:
            if attempt < 3:
                time.sleep(min(attempt, 3))
                continue
            raise CliError(
                _redact_token(
                    f"hf download failed for {file_path}: {exc.reason}", token
                )
            ) from exc
        break

    actual = dest.stat().st_size
    if remote_size > 0 and actual != remote_size:
        raise CliError(
            _redact_token(
                f"size mismatch for {file_path}: remote={remote_size} local={actual}",
                token,
            )
        )

    return actual


def _build_descriptor_payload(
    repo: str,
    revision: str,
    package_name: str,
    selected_files: List[Dict[str, Any]],
    kind_override: Optional[str],
    note: str,
    category_overrides: Dict[str, List[str]],
    use_descriptor: bool,
    civitai: Optional[Dict[str, Any]] = None,
) -> Optional[Dict[str, Any]]:
    if not use_descriptor:
        return None

    components: Dict[str, Dict[str, Any]] = {}
    components_seen: set[str] = set()

    for entry in selected_files:
        rel = entry["name"]
        categories = _infer_categories(rel, category_overrides)
        component_name = _safe_component_name(rel)

        # Keep unique component keys if two files map to the same logical component.
        candidate = component_name
        if candidate in components_seen:
            idx = 1
            while f"{candidate}-{idx}" in components_seen:
                idx += 1
            component_name = f"{candidate}-{idx}"
        components_seen.add(component_name)

        components[component_name] = {
            "path": rel,
            "comfy_categories": categories,
        }

    if not components:
        return None

    kind = _infer_kind(
        files=[entry["name"] for entry in selected_files],
        kind_override=kind_override,
    )

    descriptor: Dict[str, Any] = {
        "schema": "comfygo.model.v1",
        "name": package_name,
        "kind": kind,
        "components": components,
    }
    if repo:
        descriptor["source"] = {
            "type": "huggingface",
            "repo": repo,
            "version": revision,
        }
    else:
        descriptor["source"] = {"type": "local"}
    if civitai:
        descriptor["source"]["civitai"] = civitai

    if note:
        descriptor["notes"] = note

    return descriptor


def _write_json(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )


_LOCAL_WEIGHT_SUFFIXES = (
    ".safetensors",
    ".ckpt",
    ".bin",
    ".pt",
    ".pth",
    ".gguf",
    ".sft",
)
_SKIP_SCAN_DIR_NAMES = {".comfygo_trash", ".comfygo_views", ".git"}


def _is_model_package_dir(package_dir: Path) -> bool:
    if (package_dir / "model_index.json").is_file():
        return True
    for suffix in _LOCAL_WEIGHT_SUFFIXES:
        if any(package_dir.rglob(f"*{suffix}")):
            return True
    return False


def _list_local_package_files(package_dir: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for path in sorted(package_dir.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(package_dir)
        if any(part.startswith(".") for part in rel.parts):
            continue
        if rel.parts and rel.parts[0] == "civitai":
            continue
        name = rel.as_posix()
        lower = name.lower()
        if name == "model_index.json" or any(
            lower.endswith(suffix) for suffix in _LOCAL_WEIGHT_SUFFIXES
        ):
            rows.append({"name": name, "size": path.stat().st_size})
    return rows


def _enrich_local_package(package_dir: Path, args: argparse.Namespace) -> int:
    package_dir = package_dir.resolve()
    descriptor_path = package_dir / "comfygo-model.json"
    if descriptor_path.exists() and not args.overwrite_descriptor and args.only_missing:
        print(f"skip: {package_dir.name} already has descriptor")
        return 0

    rows = _list_local_package_files(package_dir)
    if not rows:
        print(f"skip: no model files in {package_dir}")
        return 0

    try:
        inferred_repo, inferred_revision, inferred_package_name = _read_package_state(
            package_dir
        )
    except CliError:
        inferred_repo = inferred_revision = inferred_package_name = None

    package_name = (
        args.package_name
        or inferred_package_name
        or _sanitize_path_segment(package_dir.name)
    )
    repo = inferred_repo or ""
    revision = inferred_revision or "local"
    selected = rows

    civitai = None
    civitai_token = os.getenv("CIVITAI_TOKEN") or os.getenv("CIVITAI_API_TOKEN", "")
    if civitai_token and package_name:
        civitai = _fetch_civitai(package_name, civitai_token)
        if civitai:
            print(f"Civitai match: {civitai.get('name')}")

    if args.write_descriptor:
        descriptor_payload = _build_descriptor_payload(
            repo=repo,
            revision=revision,
            package_name=package_name,
            selected_files=selected,
            kind_override=args.kind,
            note=args.descriptor_note,
            category_overrides=_split_args_file_patterns(args.category_mapping),
            use_descriptor=True,
            civitai=civitai,
        )
        if descriptor_payload:
            if descriptor_path.exists() and not args.overwrite_descriptor:
                print(
                    "Descriptor exists; skipping overwrite. Use --overwrite-descriptor to replace."
                )
            else:
                _write_json(descriptor_path, descriptor_payload)
                print(f"wrote descriptor: {descriptor_path}")

        if civitai:
            civitai_dir = package_dir / "civitai"
            civitai_dir.mkdir(parents=True, exist_ok=True)
            (civitai_dir / "info.json").write_text(
                json.dumps(civitai, indent=2) + "\n", encoding="utf-8"
            )
            print(f"wrote civitai side folder: {civitai_dir}")

    if args.write_metadata and repo:
        metadata_path = package_dir / args.metadata_file
        downloaded_paths = {row["name"]: int(row["size"]) for row in selected}
        _write_metadata(
            metadata_path,
            repo=repo,
            revision=revision,
            package_name=package_name,
            package_dir=package_dir,
            selected=selected,
            downloaded_paths=downloaded_paths,
        )
        print(f"wrote metadata: {metadata_path}")

    print(f"package root: {package_dir}")
    return 0


def _scan_models_root(models_root: Path, args: argparse.Namespace) -> int:
    if not models_root.is_dir():
        print(f"--scan-models-root is not a directory: {models_root}")
        return 1

    enriched = 0
    skipped = 0
    failures = 0

    for child in sorted(models_root.iterdir(), key=lambda path: path.name.lower()):
        if child.name.startswith(".") or child.name in _SKIP_SCAN_DIR_NAMES:
            continue
        if not child.is_dir() or not _is_model_package_dir(child):
            continue
        if args.only_missing and (child / "comfygo-model.json").exists():
            skipped += 1
            continue
        print(f"enrich: {child.name}")
        try:
            if _enrich_local_package(child, args) == 0:
                enriched += 1
            else:
                failures += 1
        except CliError as err:
            print(str(err), file=sys.stderr)
            failures += 1

    print(f"scan complete: enriched={enriched} skipped={skipped} failed={failures}")
    return 1 if failures else 0


def _write_metadata(
    path: Path,
    repo: str,
    revision: str,
    package_name: str,
    package_dir: Path,
    selected: List[Dict[str, Any]],
    downloaded_paths: Dict[str, int],
) -> None:
    payload = {
        "schema": "comfygo.download.v1",
        "source": {
            "type": "huggingface",
            "repo": repo,
            "revision": revision,
        },
        "package": {
            "name": package_name,
            "path": str(package_dir),
        },
        "selected_files": [
            {
                "path": item["name"],
                "size": int(item["size"]),
                "downloaded": int(downloaded_paths.get(item["name"], 0)),
            }
            for item in selected
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _write_json(path, payload)


def _build_file_rows(
    raw_files: List[Dict[str, Any]], skip_dotfiles: bool
) -> List[Dict[str, Any]]:
    rows = []
    for entry in raw_files:
        path = entry.get("path", "")
        if not isinstance(path, str) or not path:
            continue
        if skip_dotfiles and path.startswith("."):
            continue
        rows.append(
            {
                "name": path,
                "size": _extract_file_size(entry),
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download selected files from a Hugging Face repository using hf dry-run "
            + "verification + streaming download, with optional package-mode output for model folders."
        )
    )
    parser.add_argument(
        "repo",
        nargs="?",
        help=(
            "Hugging Face repository id, URL, or package directory path.\n"
            "Examples: user/repo, https://huggingface.co/user/repo, ."
        ),
    )
    parser.add_argument(
        "--revision", default="main", help="Repository revision (default: main)"
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Legacy mode: download files directly here (no package descriptor). "
        "When omitted, files are downloaded into package folder under --models-root.",
    )
    parser.add_argument(
        "--resume-from",
        default=None,
        help="Resume from an existing model package directory with comfygo metadata.",
    )
    parser.add_argument(
        "--models-root",
        default=None,
        help="Base models folder for package mode (default: COMFYUI_MODELS_DIR or COMFYUI_DIR/models)",
    )
    parser.add_argument(
        "--scan-models-root",
        default=None,
        help="Scan a models directory and enrich package folders missing comfygo-model.json (headless).",
    )
    parser.add_argument(
        "--package-name",
        default=None,
        help="Package folder name for package mode (default: repo base + revision).",
    )
    parser.add_argument(
        "--include",
        action="append",
        help="Glob pattern to include (can be repeated). Only matched files are shown.",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        help="Glob pattern to exclude (can be repeated).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Download all listed files without interactive selection",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="In package-mode, only list/download files that are missing or partial.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        default=True,
        help="List files recursively",
    )
    parser.add_argument(
        "--no-recursive",
        dest="recursive",
        action="store_false",
        help="List only top-level files",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only run hf dry-run checks, skip downloads",
    )
    parser.add_argument(
        "--skip-dotfiles",
        action="store_true",
        default=True,
        help="Skip dotfiles like .gitattributes (default: true)",
    )
    parser.add_argument(
        "--no-skip-dotfiles",
        dest="skip_dotfiles",
        action="store_false",
        help="Include dotfiles",
    )
    parser.add_argument(
        "--file",
        action="append",
        help="Download specific file(s) by path. Can be repeated. Skips interactive prompt.",
    )
    parser.add_argument(
        "--category-mapping",
        action="append",
        help="Map file (or glob) to comfy categories, format `path:cat1,cat2`.",
    )
    parser.add_argument(
        "--kind",
        choices=[
            "diffusers",
            "lora",
            "embedding",
            "checkpoint",
            "vae",
            "text_encoder",
            "controlnet",
            "gguf",
            "other",
        ],
        default=None,
        help="Descriptor model kind override. Omit for automatic inference.",
    )
    parser.add_argument(
        "--descriptor-note",
        default="",
        help="Optional notes text added to generated comfygo-model.json.",
    )
    parser.add_argument(
        "--write-descriptor",
        action="store_true",
        help="Write comfygo-model.json in package folder when package mode is used.",
    )
    parser.add_argument(
        "--overwrite-descriptor",
        action="store_true",
        help="Overwrite an existing comfygo-model.json file.",
    )
    parser.add_argument(
        "--metadata-file",
        default=".comfygo-download.json",
        help="Write package metadata file when package mode is used (default: .comfygo-download.json).",
    )
    parser.add_argument(
        "--write-metadata",
        action="store_true",
        help="Write .comfygo-download.json manifest in package folder when package mode is used.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.scan_models_root:
        if not args.write_descriptor:
            args.write_descriptor = True
        if not args.all:
            args.all = True
        return _scan_models_root(
            Path(args.scan_models_root).expanduser().resolve(),
            args,
        )

    source = (args.repo or "").strip()
    source_dir = _resolve_directory_arg(source)
    if source_dir is not None:
        args.resume_from = (
            str(source_dir) if args.resume_from is None else args.resume_from
        )
        repo = ""
    else:
        repo = _normalize_hf_repo(source)
    if repo and source and repo != source:
        print(f"source: {repo}")
    revision = (args.revision or "").strip() or "main"

    token = _read_token()
    category_overrides = _split_args_file_patterns(args.category_mapping)

    if args.output_dir and args.resume_from:
        print("Cannot combine --output-dir with --resume-from.")
        return 1

    package_mode = False
    package_name: str
    output_dir: Path
    if args.resume_from:
        package_dir = Path(args.resume_from).expanduser().resolve()
        if not package_dir.exists() or not package_dir.is_dir():
            print(f"--resume-from path is not a directory: {package_dir}")
            return 1
        try:
            inferred_repo, inferred_revision, inferred_package_name = (
                _read_package_state(package_dir)
            )
        except CliError as err:
            print(str(err))
            inferred_repo = inferred_revision = inferred_package_name = None

        if not repo:
            if inferred_repo is None:
                if args.write_descriptor or args.all:
                    return _enrich_local_package(package_dir, args)
                prompted = _prompt_repo()
                if not prompted:
                    print(
                        "--resume-from package does not provide source repo. "
                        "Press Enter to continue without remote downloads."
                    )
                    return 0
                repo = prompted
            else:
                repo = inferred_repo

        if args.revision == "main" and inferred_revision:
            revision = inferred_revision
        if args.package_name:
            package_name = args.package_name
        elif inferred_package_name:
            package_name = _sanitize_path_segment(inferred_package_name)
        else:
            package_name = _sanitize_path_segment(package_dir.name)

        output_dir = package_dir
        package_mode = True
    else:
        if not repo:
            current_dir = Path(".").resolve()
            inferred_repo = inferred_revision = inferred_package_name = None
            if current_dir.is_dir():
                try:
                    inferred_repo, inferred_revision, inferred_package_name = (
                        _read_package_state(current_dir)
                    )
                except CliError:
                    pass

            if inferred_repo:
                args.resume_from = str(current_dir)
                if args.revision == "main" and inferred_revision:
                    revision = inferred_revision
                if args.package_name:
                    package_name = args.package_name
                elif inferred_package_name:
                    package_name = _sanitize_path_segment(inferred_package_name)
                else:
                    package_name = _sanitize_path_segment(current_dir.name)
                output_dir = current_dir
                package_mode = True
            else:
                if not sys.stdin.isatty():
                    print("repo is required unless --resume-from is used.")
                    return 1
                repo_input = _prompt_repo()
                if not repo_input:
                    print(
                        "No repo or URL provided. Nothing to fetch in this run. "
                        "Press Enter to continue and exit."
                    )
                    return 0
                repo = repo_input

        if not package_mode:
            output_dir, package_mode, package_name = _to_output_location(
                repo=repo,
                revision=revision,
                output_dir=args.output_dir,
                models_root=args.models_root,
                package_name=args.package_name,
            )

    if package_mode and not args.write_descriptor:
        args.write_descriptor = True
    if package_mode and not args.write_metadata:
        args.write_metadata = True

    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        raw_files = _fetch_hf_tree(repo, revision, token, args.recursive)
    except CliError as err:
        print(_redact_token(str(err), token), file=sys.stderr)
        return 1

    rows = _build_file_rows(raw_files, args.skip_dotfiles)
    rows = _filter_files(rows, args.include, args.exclude)

    if package_mode:
        rows = _enrich_with_local_state(rows, output_dir)
        if args.only_missing:
            rows = [
                row for row in rows if row.get("local_status") in {"missing", "partial"}
            ]
            if not rows:
                print("No missing files found in this package folder.")
                return 0

    if args.only_missing and not package_mode:
        print("--only-missing is only supported in package mode.")
        return 1

    if not rows:
        print("No files found for the requested filters.")
        return 1

    for index, entry in enumerate(rows, start=1):
        size_text = _human_size(entry["size"]) if entry["size"] > 0 else "unknown"
        suffix = ""
        if package_mode:
            status = str(entry.get("local_status", "unknown"))
            local_size = int(entry.get("local_size", 0))
            suffix = f" [{_status_text(status, local_size, int(entry['size']))}]"
        print(f"[{index:>3}] {size_text:>10}  {entry['name']}{suffix}")

    if args.file:
        normalized = {entry["name"]: entry for entry in rows}
        selected = []
        for name in args.file:
            if name not in normalized:
                print(f"File not found: {name}", file=sys.stderr)
                return 1
            selected.append(normalized[name])
    elif args.all:
        selected = rows
    else:
        try:
            choice = input(
                "Select file numbers (comma/range, e.g. 1,3-5 or all): "
            ).strip()
        except EOFError:
            print("No selection input; aborting.")
            return 1

        if not choice:
            print("No files selected.")
            return 0

        try:
            indices = _resolve_selection(choice, len(rows))
        except CliError as err:
            print(str(err), file=sys.stderr)
            return 1
        selected = [rows[i - 1] for i in indices]
        if not selected:
            print("No files selected.")
            return 0

    print("")

    downloaded_sizes: Dict[str, int] = {}

    try:
        for item in selected:
            name = item["name"]
            size = int(item["size"])
            if package_mode and item.get("local_status") == "complete":
                downloaded_sizes[name] = int(item.get("local_size", 0))
                print(f"skip: {name} already complete")
                continue
            _run_hf_dry_run(repo, name, revision, output_dir, token)
            print(f"verified: {name}")

            if args.dry_run:
                downloaded_sizes[name] = 0
                continue

            downloaded_sizes[name] = _download_with_urllib(
                repo,
                revision,
                name,
                size,
                output_dir,
                token,
            )
            print(f"downloaded: {name}")
    except CliError as err:
        print(_redact_token(str(err), token), file=sys.stderr)
        return 1

    civitai = None
    civitai_token = os.getenv("CIVITAI_TOKEN") or os.getenv("CIVITAI_API_TOKEN", "")
    if civitai_token and package_name:
        civitai = _fetch_civitai(package_name, civitai_token)
        if civitai:
            print(f"Civitai match: {civitai.get('name')}")

    if package_mode:
        if args.write_descriptor:
            descriptor_payload = _build_descriptor_payload(
                repo=repo,
                revision=revision,
                package_name=package_name,
                selected_files=selected,
                kind_override=args.kind,
                note=args.descriptor_note,
                category_overrides=category_overrides,
                use_descriptor=True,
                civitai=civitai,
            )

            if descriptor_payload:
                descriptor_path = output_dir / "comfygo-model.json"
                if descriptor_path.exists() and not args.overwrite_descriptor:
                    print(
                        "Descriptor exists; skipping overwrite. Use --overwrite-descriptor to replace."
                    )
                else:
                    _write_json(descriptor_path, descriptor_payload)
                    print(f"wrote descriptor: {descriptor_path}")

            if civitai:
                civitai_dir = output_dir / "civitai"
                civitai_dir.mkdir(parents=True, exist_ok=True)
                (civitai_dir / "info.json").write_text(
                    json.dumps(civitai, indent=2) + "\n", encoding="utf-8"
                )
                print(f"wrote civitai side folder: {civitai_dir}")

        if args.write_metadata:
            metadata_path = output_dir / args.metadata_file
            _write_metadata(
                metadata_path,
                repo=repo,
                revision=revision,
                package_name=package_name,
                package_dir=output_dir,
                selected=selected,
                downloaded_paths=downloaded_sizes,
            )
            print(f"wrote metadata: {metadata_path}")

        print(f"package root: {output_dir}")
        print("next: comfygo models reconcile --apply")

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
