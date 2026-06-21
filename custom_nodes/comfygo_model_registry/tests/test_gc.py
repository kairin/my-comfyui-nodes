"""Tests for the GC (garbage collection) module -- dry-run reporting.

Tests verify dry-run reporting, marker detection, filtering, and
reserved/hidden folder skipping.  Quarantine/apply tests are in later
phases.
"""

from __future__ import annotations

import json
import pathlib
import time

import pytest

from custom_nodes.comfygo_model_registry import gc


@pytest.fixture
def model_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """Temporary model root for GC tests."""
    mdir = tmp_path / "models"
    mdir.mkdir(parents=True, exist_ok=True)
    return mdir


@pytest.fixture
def managed_folder(model_root: pathlib.Path) -> pathlib.Path:
    """Create a managed folder with .comfygo-download.json marker."""
    folder = model_root / "TestModel"
    folder.mkdir(exist_ok=True)
    (folder / ".comfygo-download.json").write_text(
        json.dumps({"schema": "comfygo.download.v1", "repo": "example/model"})
    )
    return folder


@pytest.fixture
def ambiguous_folder(model_root: pathlib.Path) -> pathlib.Path:
    """Create an ambiguous folder with no marker."""
    folder = model_root / "Untagged"
    folder.mkdir(exist_ok=True)
    return folder


# ── T009: dry-run with managed folders ─────────────────────────────


def test_dry_run_lists_managed_folder(managed_folder: pathlib.Path) -> None:
    """Managed folder must appear in Managed folder list."""
    model_root = managed_folder.parent
    report = gc.scan_model_root(model_root)
    names = [m.name for m in report.managed]
    assert "TestModel" in names, f"Expected TestModel in managed, got {names}"


def test_dry_run_creates_no_trash(managed_folder: pathlib.Path) -> None:
    """Dry-run must never create .comfygo_trash directory."""
    model_root = managed_folder.parent
    gc.scan_model_root(model_root)
    assert not (model_root / ".comfygo_trash").exists(), (
        "Dry-run must not create .comfygo_trash/"
    )


# ── T010: dry-run with ambiguous folders ───────────────────────────


def test_dry_run_lists_ambiguous_folder(
    ambiguous_folder: pathlib.Path,
) -> None:
    """Ambiguous folder must appear in Ambiguous list."""
    model_root = ambiguous_folder.parent
    report = gc.scan_model_root(model_root)
    names = [a.name for a in report.ambiguous]
    assert "Untagged" in names, f"Expected Untagged in ambiguous, got {names}"


def test_ambiguous_not_counted_as_managed(
    ambiguous_folder: pathlib.Path,
) -> None:
    """Ambiguous folder must NOT appear in managed list."""
    model_root = ambiguous_folder.parent
    report = gc.scan_model_root(model_root)
    names = [m.name for m in report.managed]
    assert "Untagged" not in names


# ── T011: filtered dry-run ────────────────────────────────────────


def test_filter_shows_only_matching_managed(
    model_root: pathlib.Path,
) -> None:
    """Filter -f Name should show only matching managed folder."""
    (model_root / "ModelOne").mkdir()
    (model_root / "ModelOne" / ".comfygo-download.json").write_text("{}")
    (model_root / "ModelTwo").mkdir()
    (model_root / "ModelTwo" / ".comfygo-download.json").write_text("{}")

    report = gc.scan_model_root(model_root)
    managed, ambiguous = gc._filter_report(report, "One")
    assert len(managed) == 1
    assert managed[0].name == "ModelOne"
    assert len(ambiguous) == 0


def test_filter_no_match_returns_empty(
    model_root: pathlib.Path,
) -> None:
    """Filter with no match returns empty lists."""
    (model_root / "Managed").mkdir()
    (model_root / "Managed" / ".comfygo-download.json").write_text("{}")

    report = gc.scan_model_root(model_root)
    managed, ambiguous = gc._filter_report(report, "Nonexistent")
    assert len(managed) == 0
    assert len(ambiguous) == 0


# ── T012: empty model root ────────────────────────────────────────


def test_empty_model_root(
    model_root: pathlib.Path,
) -> None:
    """Empty model root: report with zero managed and zero ambiguous."""
    report = gc.scan_model_root(model_root)
    assert len(report.managed) == 0
    assert len(report.ambiguous) == 0
    assert len(report.skipped) == 0


# ── T013: reserved / hidden folder skip ───────────────────────────


def test_reserved_folders_are_skipped(
    model_root: pathlib.Path,
) -> None:
    """Reserved ComfyUI category folders must be skipped, not ambiguous."""
    for name in ("diffusion_models", "loras", "vae", "checkpoints"):
        (model_root / name).mkdir()

    report = gc.scan_model_root(model_root)
    skipped_names = {s.name for s in report.skipped if s.reason == "reserved folder"}
    for name in ("diffusion_models", "loras", "vae", "checkpoints"):
        assert name in skipped_names, f"{name} should be skipped as reserved"


def test_reserved_folder_policy_reuses_scanner_case_insensitively(
    model_root: pathlib.Path,
) -> None:
    """GC must skip every scanner-reserved category, even with markers."""
    for name in ("ipadapter", "InsightFace", "ultralytics"):
        folder = model_root / name
        folder.mkdir()
        (folder / ".comfygo-download.json").write_text("{}")

    report = gc.scan_model_root(model_root)
    skipped_names = {
        s.name.lower() for s in report.skipped if s.reason == "reserved folder"
    }
    assert {"ipadapter", "insightface", "ultralytics"} <= skipped_names
    assert not report.managed
    assert not report.ambiguous


def test_hidden_folders_are_skipped(
    model_root: pathlib.Path,
) -> None:
    """Hidden folders must be skipped, not ambiguous."""
    (model_root / ".comfygo_views").mkdir()
    (model_root / ".hidden_folder").mkdir()

    report = gc.scan_model_root(model_root)
    skipped_hidden = {s.name for s in report.skipped if s.reason == "hidden folder"}
    assert ".comfygo_views" in skipped_hidden
    assert ".hidden_folder" in skipped_hidden


def test_report_omits_empty_sections_and_skipped_counts(
    model_root: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Silent skips must still print exactly Nothing to report."""
    (model_root / "diffusers").mkdir()

    report = gc.run_gc(model_root)

    assert not report.errors
    assert capsys.readouterr().out.strip() == "Nothing to report."


# ── T079: dry-run performance smoke ──────────────────────────────


def test_dry_run_100_folders_completes_under_one_second(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Dry-run over roughly 100 top-level folders must stay cheap."""
    root = tmp_path / "models"
    root.mkdir()
    for index in range(100):
        folder = root / f"PerfModel{index:03d}"
        folder.mkdir()
        (folder / ".comfygo-download.json").write_text("{}")

    start = time.perf_counter()
    report = gc.run_gc(root)
    elapsed = time.perf_counter() - start
    capsys.readouterr()

    assert not report.errors
    assert len(report.managed) == 100
    assert elapsed < 1.0, f"GC dry-run took {elapsed:.3f}s"
    assert not (root / ".comfygo_trash").exists()


# ── T036: invalid marker file ─────────────────────────────────────


def test_empty_download_marker_is_managed_with_warning(
    model_root: pathlib.Path,
) -> None:
    """Empty .comfygo-download.json: still managed but warns."""
    folder = model_root / "BadJson"
    folder.mkdir()
    (folder / ".comfygo-download.json").write_text("")

    report = gc.scan_model_root(model_root)
    assert len(report.managed) == 1
    assert report.managed[0].name == "BadJson"
    assert not report.managed[0].markers[0].parseable
    assert any("unparseable" in w.lower() for w in report.warnings)


def test_invalid_json_marker_is_managed_with_warning(
    model_root: pathlib.Path,
) -> None:
    """Malformed JSON marker: still managed but warns."""
    folder = model_root / "BadJson2"
    folder.mkdir()
    (folder / ".comfygo-download.json").write_text("{not-valid")

    report = gc.scan_model_root(model_root)
    assert len(report.managed) == 1
    assert not report.managed[0].markers[0].parseable
    assert any("unparseable" in w.lower() for w in report.warnings)


def test_invalid_descriptor_marker_is_managed_with_warning(
    model_root: pathlib.Path,
) -> None:
    """Malformed comfygo-model.json marker: still managed but warns."""
    folder = model_root / "BadDescriptor"
    folder.mkdir()
    (folder / "comfygo-model.json").write_text("{not-valid")

    report = gc.scan_model_root(model_root)

    assert len(report.managed) == 1
    assert report.managed[0].name == "BadDescriptor"
    assert len(report.managed[0].markers) == 1
    assert report.managed[0].markers[0].type == "descriptor"
    assert not report.managed[0].markers[0].parseable
    assert any("unparseable descriptor marker" in w for w in report.warnings)


# ═══════════════════════════════════════════════════════════════════
# US3 — Quarantine apply tests
# ═══════════════════════════════════════════════════════════════════

import errno  # noqa: E402
import os  # noqa: E402
from datetime import date  # noqa: E402


def _make_managed(name: str, root: pathlib.Path) -> gc.ManagedFolder:
    """Helper: create a managed folder and return the entity."""
    root.mkdir(parents=True, exist_ok=True)
    folder = root / name
    folder.mkdir()
    (folder / ".comfygo-download.json").write_text(
        json.dumps({"schema": "comfygo.download.v1"})
    )
    markers = gc.detect_markers(folder)
    return gc.ManagedFolder(name=name, path=folder, markers=markers)


def _today_iso() -> str:
    return date.today().isoformat()


# ── T018: quarantine apply ────────────────────────────────────────


def test_apply_quarantine_moves_folder(tmp_path: pathlib.Path) -> None:
    """-f NAME --apply moves the folder to .comfygo_trash/date/name/."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)  # noqa: F841 (var only for side effects in helper)

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert not report.errors, f"Unexpected errors: {report.errors}"
    assert report.selected_target is not None
    assert report.selected_target.name == "TestModel"
    assert len(report.operations) == 1
    assert report.operations[0].status == "completed"
    assert not (root / "TestModel").exists(), "Source should be gone"
    assert (root / ".comfygo_trash").is_dir()
    dest = root / ".comfygo_trash" / _today_iso() / "TestModel"
    assert dest.is_dir(), f"Expected {dest}"
    assert report.operations[0].destination == dest
    assert report.quarantined == str(dest)


# ── T019: idempotency ─────────────────────────────────────────────


def test_apply_idempotent(tmp_path: pathlib.Path) -> None:
    """Second apply on quarantined folder produces error."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)

    report1 = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert not report1.errors

    report2 = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert report2.errors
    assert any("no managed" in e.lower() for e in report2.errors)


# ── T020: missing target ──────────────────────────────────────────


def test_apply_missing_target(tmp_path: pathlib.Path) -> None:
    """-f Nonexistent --apply reports error."""
    root = tmp_path / "models"
    root.mkdir()
    report = gc.run_gc(root, filter_str="Nonexistent", apply=True)
    assert report.errors


# ── T021: ambiguous folder rejection ──────────────────────────────


def test_apply_rejects_ambiguous(tmp_path: pathlib.Path) -> None:
    """-f Ambiguous --apply when no markers: error."""
    root = tmp_path / "models"
    (root / "Ambiguous").mkdir(parents=True, exist_ok=True)

    report = gc.run_gc(root, filter_str="Ambiguous", apply=True)
    assert report.errors
    assert any("not managed" in e.lower() for e in report.errors)


# ── T022: .comfygo_trash auto-creation ────────────────────────────


def test_apply_creates_trash_if_absent(tmp_path: pathlib.Path) -> None:
    """--apply creates .comfygo_trash automatically."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)
    assert not (root / ".comfygo_trash").exists()

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert not report.errors
    assert (root / ".comfygo_trash").is_dir()


# ── T023: destination collision ───────────────────────────────────


def test_apply_destination_collision_uses_suffix(
    tmp_path: pathlib.Path,
) -> None:
    """If trash destination exists, append -1 suffix."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)  # noqa: F841 (var only for side effects in helper)

    trash_date = root / ".comfygo_trash" / _today_iso()
    trash_date.mkdir(parents=True)
    (trash_date / "TestModel").mkdir()

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert not report.errors
    dest = trash_date / "TestModel-1"
    assert dest.is_dir(), f"Expected collision suffix, got no {dest}"
    assert any("TestModel-1" in w for w in report.warnings)


# ── T024: symlinked .comfygo_trash rejection ──────────────────────


def test_apply_rejects_symlinked_trash(tmp_path: pathlib.Path) -> None:
    """Refuse to operate if .comfygo_trash is a symlink."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)

    real = tmp_path / "real-trash"
    real.mkdir()
    trash = root / ".comfygo_trash"
    trash.symlink_to(real, target_is_directory=True)

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert report.errors


# ── T025: cross-filesystem failure (EXDEV) ────────────────────────


def test_apply_exdev_reported_as_error(tmp_path: pathlib.Path, monkeypatch) -> None:
    """Cross-filesystem rename: error, no files changed."""
    root = tmp_path / "models"
    mf = _make_managed("TestModel", root)

    def _mock_rename(src, dst):
        raise OSError(errno.EXDEV, "Cross-device link")

    monkeypatch.setattr(os, "rename", _mock_rename)

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert report.errors
    assert any("cross" in e.lower() for e in report.errors)
    assert mf.path.is_dir(), "Source must not be deleted on EXDEV"


# ── T037: multi-managed match rejection ──────────────────────────


def test_apply_multi_match_rejects(tmp_path: pathlib.Path) -> None:
    """Two managed folders matching filter: error, list both."""
    root = tmp_path / "models"
    _make_managed("ModelOne", root)
    _make_managed("ModelTwo", root)

    report = gc.run_gc(root, filter_str="Model", apply=True)
    assert report.errors
    assert any("multiple" in e.lower() for e in report.errors)
    assert (root / "ModelOne").is_dir(), "Must not move when ambiguous"
    assert (root / "ModelTwo").is_dir(), "Must not move when ambiguous"


# ── T038: source symlink refusal ──────────────────────────────────


def test_scan_skips_source_symlink(tmp_path: pathlib.Path) -> None:
    """Source entry that is a symlink must be skipped."""
    root = tmp_path / "models"
    root.mkdir()
    real = tmp_path / "real-folder"
    real.mkdir()
    (real / ".comfygo-download.json").write_text("{}")
    (root / "LinkedModel").symlink_to(real, target_is_directory=True)

    report = gc.scan_model_root(root)
    skipped_names = {s.name for s in report.skipped if s.reason == "source symlink"}
    assert "LinkedModel" in skipped_names
    assert not any(m.name == "LinkedModel" for m in report.managed)


def test_unfiltered_dry_run_source_symlink_warns_without_error(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unfiltered dry-run reports source symlinks as non-fatal warnings."""
    root = tmp_path / "models"
    root.mkdir()
    real = tmp_path / "real-folder"
    real.mkdir()
    (real / ".comfygo-download.json").write_text("{}")
    linked = root / "LinkedModel"
    linked.symlink_to(real, target_is_directory=True)

    report = gc.run_gc(root)
    out = capsys.readouterr().out

    assert not report.errors
    assert f"warning: Refusing to quarantine symlinked folder '{linked}'" in out
    assert not (root / ".comfygo_trash").exists()


def test_filtered_dry_run_source_symlink_is_error(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Filtered dry-run targeting only a source symlink exits via error."""
    root = tmp_path / "models"
    root.mkdir()
    real = tmp_path / "real-folder"
    real.mkdir()
    (real / ".comfygo-download.json").write_text("{}")
    linked = root / "LinkedModel"
    linked.symlink_to(real, target_is_directory=True)

    report = gc.run_gc(root, filter_str="LinkedModel")
    out = capsys.readouterr().out

    warning = f"warning: Refusing to quarantine symlinked folder '{linked}'"
    assert warning in report.errors
    assert warning in out
    assert not (root / ".comfygo_trash").exists()


def test_apply_source_symlink_is_error(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Apply targeting only a source symlink fails with no mutation."""
    root = tmp_path / "models"
    root.mkdir()
    real = tmp_path / "real-folder"
    real.mkdir()
    (real / ".comfygo-download.json").write_text("{}")
    linked = root / "LinkedModel"
    linked.symlink_to(real, target_is_directory=True)

    report = gc.run_gc(root, filter_str="LinkedModel", apply=True)
    out = capsys.readouterr().out

    warning = f"warning: Refusing to quarantine symlinked folder '{linked}'"
    assert warning in report.errors
    assert warning in out
    assert linked.is_symlink()
    assert not (root / ".comfygo_trash").exists()


def test_quarantine_refuses_non_top_level_source(
    tmp_path: pathlib.Path,
) -> None:
    """The mutating primitive must independently reject nested sources."""
    root = tmp_path / "models"
    nested_parent = root / "Parent"
    folder = nested_parent / "NestedModel"
    folder.mkdir(parents=True)
    (folder / ".comfygo-download.json").write_text("{}")
    managed = gc.ManagedFolder(
        name="NestedModel",
        path=folder,
        markers=gc.detect_markers(folder),
    )

    with pytest.raises(OSError):
        gc.quarantine(managed, root)

    assert folder.is_dir()
    assert not (root / ".comfygo_trash").exists()


def test_quarantine_refuses_source_symlink_primitive(
    tmp_path: pathlib.Path,
) -> None:
    """The mutating primitive must reject symlink sources before trash setup."""
    root = tmp_path / "models"
    root.mkdir()
    real = tmp_path / "real-folder"
    real.mkdir()
    (real / ".comfygo-download.json").write_text("{}")
    linked = root / "LinkedModel"
    linked.symlink_to(real, target_is_directory=True)
    managed = gc.ManagedFolder(
        name="LinkedModel",
        path=linked,
        markers=gc.detect_markers(linked),
    )

    with pytest.raises(OSError):
        gc.quarantine(managed, root)

    assert linked.is_symlink()
    assert not (root / ".comfygo_trash").exists()


def test_filtered_dry_run_no_match_records_error(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Filtered dry-run with no visible match must be a CLI error."""
    root = tmp_path / "models"
    _make_managed("TestModel", root)

    report = gc.run_gc(root, filter_str="Missing")
    out = capsys.readouterr().out

    assert report.errors
    assert "No folders matching 'Missing'" in report.errors[0]
    assert "error: No folders matching 'Missing'" in out
    assert not (root / ".comfygo_trash").exists()


# ── T039: --apply without -f ──────────────────────────────────────


def test_apply_without_filter_fails(tmp_path: pathlib.Path) -> None:
    """gc --apply without -f reports error, no mutation."""
    root = tmp_path / "models"
    root.mkdir()
    _make_managed("TestModel", root)

    report = gc.run_gc(root, apply=True, filter_str=None)
    assert report.errors
    assert (root / "TestModel").is_dir(), "Folder must not be moved"
    assert not (root / ".comfygo_trash").exists(), "No trash on bare --apply"


# ── T042: Permission failure test ────────────────────────────────


def test_apply_permission_error_reported(tmp_path: pathlib.Path, monkeypatch) -> None:
    """Permission error on rename: error, source left in place."""
    root = tmp_path / "models"
    mf = _make_managed("TestModel", root)

    def _mock_rename(src, dst):
        raise OSError(errno.EACCES, "Permission denied")

    monkeypatch.setattr(os, "rename", _mock_rename)

    report = gc.run_gc(root, filter_str="TestModel", apply=True)
    assert report.errors
    assert mf.path.is_dir(), "Source must not be deleted on permission error"


def test_apply_unsafe_source_name_is_controlled_error(
    tmp_path: pathlib.Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsafe source name fails closed without traceback or trash creation."""
    root = tmp_path / "models"
    mf = _make_managed("~UnsafeModel", root)

    report = gc.run_gc(root, filter_str="~UnsafeModel", apply=True)
    out = capsys.readouterr().out

    expected = "error: Unsafe path segment: '~UnsafeModel'; no files changed"
    assert report.errors == ["Unsafe path segment: '~UnsafeModel'; no files changed"]
    assert expected in out
    assert "Traceback" not in out
    assert mf.path.is_dir(), "Unsafe source must remain in place"
    assert not (root / ".comfygo_trash").exists()
