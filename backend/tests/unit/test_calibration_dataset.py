from pathlib import Path

import pytest

from app.modules.calibration.dataset import (
    DatasetValidationError,
    load_annotation_package,
    validate_manifest,
)


def _datasets_root() -> Path:
    mounted = Path("/datasets")
    if mounted.is_dir():
        return mounted
    return Path(__file__).resolve().parents[3] / "datasets"


REPO_DATASETS = _datasets_root()
ANNOTATION = (
    REPO_DATASETS / "annotations" / "glass_500ml_v1" / "v1.json"
)
RAW_DIR = REPO_DATASETS / "raw" / "glass_500ml_v1"


@pytest.mark.skipif(
    not ANNOTATION.is_file() or not RAW_DIR.is_dir(),
    reason="Local glass_500ml_v1 dataset not present",
)
def test_load_glass_500ml_annotation_package() -> None:
    package = load_annotation_package(
        datasets_root=REPO_DATASETS,
        annotation_relative_path="annotations/glass_500ml_v1/v1.json",
    )
    assert package.dataset_id == "glass_500ml_v1"
    assert package.nominal_volume_ml == 500
    assert package.step_ml == 62.5
    assert len(package.points) == 8
    assert package.points[0]["true_ml"] == 62.5
    assert package.points[-1]["true_ml"] == 500.0
    for point in package.points:
        assert Path(point["absolute_path"]).is_file()
        assert "capture_metadata" in point


@pytest.mark.skipif(
    not (RAW_DIR / "manifest.json").is_file(),
    reason="Local glass_500ml_v1 manifest not present",
)
def test_validate_glass_manifest() -> None:
    package = validate_manifest(dataset_dir=RAW_DIR)
    assert len(package.points) == 8


def test_annotation_rejects_path_traversal(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    root.mkdir()
    with pytest.raises(DatasetValidationError):
        load_annotation_package(
            datasets_root=root,
            annotation_relative_path="../secret.json",
        )
