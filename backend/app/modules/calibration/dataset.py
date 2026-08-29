from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class DatasetValidationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class ValidatedCalibrationDataset:
    dataset_id: str
    dataset_version: str
    vessel: str | None
    nominal_volume_ml: int | None
    step_ml: float | None
    notes: str | None
    calibration_method: str | None
    raw_dir: Path
    points: list[dict[str, Any]]


def load_annotation_package(
    *,
    datasets_root: Path,
    annotation_relative_path: str,
) -> ValidatedCalibrationDataset:
    """
    Load a versioned annotation JSON and verify raw images exist.

    true_ml values are trusted as externally measured labels from the package;
    they are never inferred by vision.
    """
    root = datasets_root.resolve()
    relative = annotation_relative_path.replace("\\", "/").lstrip("/")
    if ".." in relative.split("/"):
        raise DatasetValidationError("Invalid annotation path.")

    annotation_path = (root / relative).resolve()
    if not str(annotation_path).startswith(str(root)):
        raise DatasetValidationError("Annotation path escapes datasets root.")
    if not annotation_path.is_file():
        raise DatasetValidationError(
            f"Annotation file not found: {relative}"
        )

    try:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(
            "Annotation JSON is invalid."
        ) from exc

    return validate_annotation_payload(root=root, payload=payload)


def validate_annotation_payload(
    *,
    root: Path,
    payload: dict[str, Any],
) -> ValidatedCalibrationDataset:
    required = ("dataset_id", "dataset_version", "points", "raw_dir")
    for key in required:
        if key not in payload:
            raise DatasetValidationError(
                f"Annotation missing required field: {key}"
            )

    points = payload["points"]
    if not isinstance(points, list) or not points:
        raise DatasetValidationError("Annotation points must be a non-empty list.")

    raw_rel = str(payload["raw_dir"]).replace("\\", "/").lstrip("/")
    if ".." in raw_rel.split("/"):
        raise DatasetValidationError("Invalid raw_dir in annotation.")
    raw_dir = (root / raw_rel).resolve()
    if not str(raw_dir).startswith(str(root)):
        raise DatasetValidationError("raw_dir escapes datasets root.")
    if not raw_dir.is_dir():
        raise DatasetValidationError(f"Raw dataset directory missing: {raw_rel}")

    normalized_points: list[dict[str, Any]] = []
    seen_images: set[str] = set()
    seen_ml: set[float] = set()

    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise DatasetValidationError(f"Point {index} must be an object.")
        if "true_ml" not in point or "image" not in point:
            raise DatasetValidationError(
                f"Point {index} requires true_ml and image."
            )
        try:
            true_ml = float(point["true_ml"])
        except (TypeError, ValueError) as exc:
            raise DatasetValidationError(
                f"Point {index} has invalid true_ml."
            ) from exc
        if true_ml < 0:
            raise DatasetValidationError(
                f"Point {index} true_ml must be >= 0."
            )

        image = str(point["image"]).replace("\\", "/")
        if "/" in image or image.startswith(".."):
            raise DatasetValidationError(
                f"Point {index} image must be a plain filename."
            )
        if image in seen_images:
            raise DatasetValidationError(
                f"Duplicate image in annotation: {image}"
            )
        if true_ml in seen_ml:
            raise DatasetValidationError(
                f"Duplicate true_ml in annotation: {true_ml}"
            )

        image_path = raw_dir / image
        if not image_path.is_file():
            raise DatasetValidationError(
                f"Missing raw image for true_ml={true_ml}: {image}"
            )

        metadata = point.get("capture_metadata") or {}
        if not isinstance(metadata, dict):
            raise DatasetValidationError(
                f"Point {index} capture_metadata must be an object."
            )

        seen_images.add(image)
        seen_ml.add(true_ml)
        normalized_points.append(
            {
                "true_ml": true_ml,
                "image": image,
                "capture_metadata": metadata,
                "absolute_path": str(image_path),
            }
        )

    normalized_points.sort(key=lambda item: item["true_ml"])

    return ValidatedCalibrationDataset(
        dataset_id=str(payload["dataset_id"]),
        dataset_version=str(payload["dataset_version"]),
        vessel=payload.get("vessel"),
        nominal_volume_ml=(
            int(payload["nominal_volume_ml"])
            if payload.get("nominal_volume_ml") is not None
            else None
        ),
        step_ml=(
            float(payload["step_ml"])
            if payload.get("step_ml") is not None
            else None
        ),
        notes=payload.get("notes"),
        calibration_method=payload.get("calibration_method"),
        raw_dir=raw_dir,
        points=normalized_points,
    )


def validate_manifest(
    *,
    dataset_dir: Path,
) -> ValidatedCalibrationDataset:
    """Validate a raw folder that contains manifest.json."""
    manifest_path = dataset_dir / "manifest.json"
    if not manifest_path.is_file():
        raise DatasetValidationError("manifest.json not found in dataset dir.")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError("manifest.json is invalid JSON.") from exc

    root = dataset_dir.parent.parent if dataset_dir.parent.name == "raw" else dataset_dir.parent
    # Build annotation-shaped payload from manifest for shared validation.
    images = manifest.get("images")
    if not isinstance(images, list):
        raise DatasetValidationError("manifest.images must be a list.")

    payload = {
        "dataset_id": manifest.get("profile") or dataset_dir.name,
        "dataset_version": "manifest",
        "vessel": manifest.get("vessel"),
        "nominal_volume_ml": manifest.get("nominal_volume_ml"),
        "step_ml": manifest.get("step_ml"),
        "notes": manifest.get("notes"),
        "raw_dir": str(dataset_dir.relative_to(root)).replace("\\", "/"),
        "points": [
            {
                "true_ml": item.get("true_ml"),
                "image": item.get("file"),
                "capture_metadata": item.get("capture_metadata") or {},
            }
            for item in images
        ],
    }
    return validate_annotation_payload(root=root, payload=payload)
