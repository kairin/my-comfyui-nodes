"""Tests for the reconciler — symlink generation, idempotency, conflict handling."""

from __future__ import annotations

import pathlib

from custom_nodes.comfygo_model_registry import models
from custom_nodes.comfygo_model_registry import reconciler
from custom_nodes.comfygo_model_registry import compat_views


def _make_package(
    name: str,
    tmp_path: pathlib.Path,
    components: list[tuple[str, list[str]]] | None = None,
) -> models.ModelPackage:
    """Create a ModelPackage with a real folder under tmp_path."""
    folder = tmp_path / name
    folder.mkdir(parents=True, exist_ok=True)
    comp_list: list[models.Component] = []
    for logical_name, categories in (components or []):
        comp_dir = folder / logical_name
        comp_dir.mkdir(exist_ok=True)
        comp_list.append(
            models.Component(
                logical_name=logical_name,
                relative_path=pathlib.Path(logical_name),
                comfy_categories=list(categories),
            )
        )
    return models.ModelPackage(
        name=name,
        path=folder.resolve(),
        kind=models.ModelKind.DIFFUSERS,
        components=comp_list,
        detection_method=models.DetectionMethod.DIFFUSERS_INFERENCE,
    )


class TestReconcileDryRun:
    def test_dry_run_reports_pending_views(self, tmp_path: pathlib.Path) -> None:
        """Dry-run should report views that need to be created."""
        pkgs = [_make_package("TestModel", tmp_path, [("transformer", ["diffusion_models"])])]
        report = reconciler.reconcile(pkgs, tmp_path, dry_run=True)
        # Even in dry-run, views_created lists what WOULD be created.
        assert len(report.views_created) == 1
        assert report.views_pruned == 0

    def test_dry_run_reports_new_views(self, tmp_path: pathlib.Path) -> None:
        """Dry-run should report what would be created."""
        pkgs = [
            _make_package(
                "MyModel",
                tmp_path,
                [("transformer", ["diffusion_models"]), ("vae", ["vae"])],
            )
        ]
        report = reconciler.reconcile(pkgs, tmp_path, dry_run=True)
        assert len(report.views_created) == 2


class TestReconcileApply:
    def test_creates_symlinks(self, tmp_path: pathlib.Path) -> None:
        pkgs = [
            _make_package(
                "MyModel",
                tmp_path,
                [("transformer", ["diffusion_models"])],
            )
        ]
        report = reconciler.reconcile(pkgs, tmp_path, dry_run=False)
        assert len(report.views_created) == 1
        link = (
            compat_views.views_root(tmp_path)
            / "diffusion_models"
            / "MyModel"
            / "transformer"
        )
        assert link.is_symlink()
        assert link.resolve() == (tmp_path / "MyModel" / "transformer").resolve()

    def test_idempotency(self, tmp_path: pathlib.Path) -> None:
        """Re-running apply must produce identical state without errors."""
        pkgs = [
            _make_package(
                "IdempotentModel",
                tmp_path,
                [("vae", ["vae"])],
            )
        ]
        report1 = reconciler.reconcile(pkgs, tmp_path, dry_run=False)
        assert len(report1.views_created) == 1

        report2 = reconciler.reconcile(pkgs, tmp_path, dry_run=False)
        # Second run: 0 new views (already exist), but no errors.
        assert len(report2.views_created) == 0
        # The report should show idempotent state.
        assert report2.views_pruned == 0

    def test_prunes_stale_symlinks(self, tmp_path: pathlib.Path) -> None:
        """Removing a model package should prune its views."""
        pkgs = [
            _make_package(
                "StaleModel",
                tmp_path,
                [("transformer", ["diffusion_models"])],
            )
        ]
        reconciler.reconcile(pkgs, tmp_path, dry_run=False)

        # Now reconcile without the package — the stale view should be pruned.
        report = reconciler.reconcile([], tmp_path, dry_run=False)
        assert report.views_pruned >= 1

    def test_skips_broken_component(self, tmp_path: pathlib.Path) -> None:
        """A component whose path doesn't exist should be skipped."""
        folder = tmp_path / "BrokenModel"
        folder.mkdir()
        pkg = models.ModelPackage(
            name="BrokenModel",
            path=folder.resolve(),
            kind=models.ModelKind.DIFFUSERS,
            components=[
                models.Component(
                    logical_name="nonexistent",
                    relative_path=pathlib.Path("does_not_exist"),
                    comfy_categories=["diffusion_models"],
                )
            ],
            detection_method=models.DetectionMethod.DIFFUSERS_INFERENCE,
        )
        report = reconciler.reconcile([pkg], tmp_path, dry_run=False)
        assert len(report.warnings) >= 1
        assert len(report.views_created) == 0

    def test_skips_component_symlink_escape(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A component symlink resolving outside the model root is skipped."""
        folder = tmp_path / "EscapeModel"
        folder.mkdir()
        outside = tmp_path.parent / f"{tmp_path.name}_outside"
        outside.mkdir()
        (folder / "escaped").symlink_to(outside, target_is_directory=True)

        pkg = models.ModelPackage(
            name="EscapeModel",
            path=folder.resolve(),
            kind=models.ModelKind.DIFFUSERS,
            components=[
                models.Component(
                    logical_name="escaped",
                    relative_path=pathlib.Path("escaped"),
                    comfy_categories=["diffusion_models"],
                )
            ],
            detection_method=models.DetectionMethod.DIFFUSERS_INFERENCE,
        )

        report = reconciler.reconcile([pkg], tmp_path, dry_run=False)

        assert len(report.views_created) == 0
        assert report.warnings
        assert not (
            compat_views.views_root(tmp_path)
            / "diffusion_models"
            / "EscapeModel"
            / "escaped"
        ).exists()


class TestConflictHandling:
    def test_conflict_two_packages_same_view(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Two packages whose components map to the same view path."""
        pkg_a = _make_package(
            "ConflictModel", tmp_path, [("transformer", ["diffusion_models"])]
        )
        # Second package: same name and same component name → same view.
        pkg_b = _make_package(
            "ConflictModel",
            tmp_path / "sub",
            [("transformer", ["diffusion_models"])],
        )
        report = reconciler.reconcile([pkg_a, pkg_b], tmp_path, dry_run=False)
        # First package wins; second is reported as a conflict.
        assert len(report.views_created) == 1
        assert len(report.conflicts) >= 1

    def test_different_components_no_conflict(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Same model name but different component names."""
        pkg_a = _make_package(
            "SharedName", tmp_path, [("transformer", ["diffusion_models"])]
        )
        pkg_b = _make_package(
            "SharedName",
            tmp_path / "sub",
            [("unet", ["diffusion_models"]), ("vae", ["vae"])],
        )
        report = reconciler.reconcile([pkg_a, pkg_b], tmp_path, dry_run=False)
        # No conflicts because component names differ.
        assert len(report.conflicts) == 0


class TestIdempotencyReporting:
    def test_reapply_reports_no_new_created(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Re-running apply on already-correct state reports 0 created."""
        pkg = _make_package(
            "IdempotentModel", tmp_path, [("transformer", ["diffusion_models"])]
        )
        # First apply: should create the view.
        r1 = reconciler.reconcile([pkg], tmp_path, dry_run=False)
        assert len(r1.views_created) == 1

        # Second apply: view already exists and is correct.
        r2 = reconciler.reconcile([pkg], tmp_path, dry_run=False)
        # The view already points to the right target, so create_view
        # returns None, and views_created should be 0.
        assert len(r2.views_created) == 0
        assert r2.views_pruned == 0


class TestGroupedViews:
    def test_views_grouped_correctly(self, tmp_path: pathlib.Path) -> None:
        """Views should be organized by category, then model name."""
        pkgs = [
            _make_package(
                "ModelA",
                tmp_path,
                [("transformer", ["diffusion_models"]), ("vae", ["vae"])],
            ),
            _make_package(
                "ModelB",
                tmp_path,
                [("text_encoder", ["text_encoders"])],
            ),
        ]
        reconciler.reconcile(pkgs, tmp_path, dry_run=False)

        vroot = compat_views.views_root(tmp_path)
        assert (vroot / "diffusion_models" / "ModelA" / "transformer").is_symlink()
        assert (vroot / "vae" / "ModelA" / "vae").is_symlink()
        assert (vroot / "text_encoders" / "ModelB" / "text_encoder").is_symlink()


class TestViewSafety:
    def test_rejects_symlinked_views_root(
        self, tmp_path: pathlib.Path
    ) -> None:
        """A symlinked .comfygo_views root must stop all view operations."""
        outside = tmp_path / "outside-views"
        outside.mkdir()
        compat_views.views_root(tmp_path).symlink_to(
            outside, target_is_directory=True
        )
        pkgs = [
            _make_package(
                "SafeModel",
                tmp_path,
                [("transformer", ["diffusion_models"])],
            )
        ]

        report = reconciler.reconcile(pkgs, tmp_path, dry_run=False)

        assert len(report.views_created) == 0
        assert report.warnings
        assert not (
            outside / "diffusion_models" / "SafeModel" / "transformer"
        ).exists()

    def test_dry_run_skips_symlinked_view_dirs(
        self, tmp_path: pathlib.Path
    ) -> None:
        """Dry-run stale pruning must not traverse symlinked view dirs."""
        vroot = compat_views.views_root(tmp_path)
        vroot.mkdir()
        outside = tmp_path / "outside-category"
        outside.mkdir()
        (vroot / "diffusion_models").symlink_to(
            outside, target_is_directory=True
        )

        report = reconciler.reconcile([], tmp_path, dry_run=True)

        assert report.views_pruned == 0
        assert report.warnings
