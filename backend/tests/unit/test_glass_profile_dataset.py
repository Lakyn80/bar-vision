import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.vision.glass_profile.dataset import (
    audit_glass_profile_dataset,
    create_deterministic_split,
)
from app.vision.glass_profile.schema import (
    GlassProfileAnnotationError,
    load_glass_profile_annotations,
    parse_glass_profile_annotations,
)


REPO_DATASETS = Path(__file__).resolve().parents[3] / "datasets"
ANNOTATION = REPO_DATASETS / "annotations" / "glass_500ml_v1" / "v1.json"


@pytest.mark.skipif(
    not ANNOTATION.exists(),
    reason="Local glass_500ml_v1 annotations not present",
)
def test_current_glass_dataset_audit_reports_missing_ml_labels() -> None:
    document = load_glass_profile_annotations(
        datasets_root=REPO_DATASETS,
        annotation_relative_path="annotations/glass_500ml_v1/v1.json",
    )

    audit = audit_glass_profile_dataset(document, inspect_images=True)

    assert audit.dataset_id == "glass_500ml_v1"
    assert audit.schema_version == "legacy-calibration-v1"
    assert audit.total_samples == 8
    assert audit.positive_samples == 8
    assert audit.negative_samples == 0
    assert audit.samples_with_bbox == 0
    assert audit.samples_with_mask == 0
    assert audit.samples_with_keypoints == 0
    assert audit.ready_for_fine_tuning is False
    assert any("negative" in reason for reason in audit.blocking_reasons)
    assert any("bbox" in reason for reason in audit.blocking_reasons)
    assert any("mask" in reason for reason in audit.blocking_reasons)
    assert any("keypoints" in reason for reason in audit.blocking_reasons)
    assert {shape.width for shape in audit.image_shapes} == {960}
    assert {shape.height for shape in audit.image_shapes} == {1280}


def test_deterministic_split_is_stable_and_disjoint() -> None:
    document = load_glass_profile_annotations(
        datasets_root=REPO_DATASETS,
        annotation_relative_path="annotations/glass_500ml_v1/v1.json",
    )

    first = create_deterministic_split(
        document.samples,
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        seed=20260829,
    )
    second = create_deterministic_split(
        document.samples,
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        seed=20260829,
    )

    assert first == second
    train = set(first.train)
    validation = set(first.validation)
    test = set(first.test)
    assert train
    assert validation
    assert test
    assert train.isdisjoint(validation)
    assert train.isdisjoint(test)
    assert validation.isdisjoint(test)
    assert any("capture_session_id missing" in item for item in first.warnings)


def test_geometry_annotation_v2_audits_as_training_ready(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    raw_dir = root / "raw" / "glass_500ml_v1"
    raw_dir.mkdir(parents=True)
    for filename in ("valid.jpg", "bottle.jpg", "background.jpg"):
        image = np.full((64, 64, 3), 230, dtype=np.uint8)
        cv2.imwrite(str(raw_dir / filename), image)

    payload = {
        "schema_version": "glass-profile-annotation-v2",
        "dataset_id": "glass_500ml_v1",
        "dataset_version": "unit",
        "profile_key": "glass_500ml_v1",
        "raw_dir": "raw/glass_500ml_v1",
        "samples": [
            {
                "image": "valid.jpg",
                "profile": "glass_500ml_v1",
                "label": "valid_glass",
                "capture_session_id": "session-valid",
                "bbox": [0.30, 0.12, 0.70, 0.90],
                "keypoints": {
                    "rim_left": [0.38, 0.20, 1.0],
                    "rim_right": [0.62, 0.20, 1.0],
                    "bottom_left": [0.36, 0.82, 1.0],
                    "bottom_right": [0.64, 0.82, 1.0],
                    "rim_center": [0.50, 0.20, 1.0],
                    "bottom_center": [0.50, 0.82, 1.0]
                },
                "mask": {
                    "type": "polygon",
                    "coordinate_space": "normalized",
                    "points": [
                        [0.38, 0.20],
                        [0.62, 0.20],
                        [0.64, 0.82],
                        [0.36, 0.82]
                    ]
                }
            },
            {
                "image": "bottle.jpg",
                "profile": "glass_500ml_v1",
                "label": "bottle",
                "capture_session_id": "session-bottle"
            },
            {
                "image": "background.jpg",
                "profile": "glass_500ml_v1",
                "label": "no_glass",
                "capture_session_id": "session-background"
            }
        ]
    }

    document = parse_glass_profile_annotations(
        datasets_root=root,
        payload=payload,
    )
    audit = audit_glass_profile_dataset(document)

    assert audit.ready_for_fine_tuning is True
    assert audit.positive_samples == 1
    assert audit.negative_samples == 2
    assert audit.samples_with_bbox == 1
    assert audit.samples_with_mask == 1
    assert audit.samples_with_keypoints == 1


def test_annotation_rejects_absolute_windows_paths(tmp_path: Path) -> None:
    root = tmp_path / "datasets"
    (root / "raw" / "glass_500ml_v1").mkdir(parents=True)

    payload = {
        "schema_version": "glass-profile-annotation-v2",
        "dataset_id": "glass_500ml_v1",
        "dataset_version": "unit",
        "profile_key": "glass_500ml_v1",
        "raw_dir": "C:/private/raw/glass_500ml_v1",
        "samples": []
    }

    with pytest.raises(GlassProfileAnnotationError):
        parse_glass_profile_annotations(datasets_root=root, payload=payload)


def test_committed_split_matches_loader_strategy() -> None:
    document = load_glass_profile_annotations(
        datasets_root=REPO_DATASETS,
        annotation_relative_path="annotations/glass_500ml_v1/v1.json",
    )
    split = create_deterministic_split(
        document.samples,
        dataset_id=document.dataset_id,
        dataset_version=document.dataset_version,
        seed=20260829,
        split_version="glass_500ml_v1-v1-seed-20260829",
    )
    committed = json.loads(
        (REPO_DATASETS / "splits" / "glass_500ml_v1" / "v1.json").read_text(
            encoding="utf-8",
        )
    )

    assert committed["train"] == list(split.train)
    assert committed["validation"] == list(split.validation)
    assert committed["test"] == list(split.test)
