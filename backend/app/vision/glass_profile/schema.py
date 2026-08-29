from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


GLASS_500ML_PROFILE_KEY = "glass_500ml_v1"

KEYPOINT_NAMES: tuple[str, ...] = (
    "rim_left",
    "rim_right",
    "bottom_left",
    "bottom_right",
    "rim_center",
    "bottom_center",
)

POSITIVE_LABELS = {"valid_glass"}
NEGATIVE_LABELS = {
    "no_glass",
    "wrong_glass",
    "different_glass",
    "cup",
    "bottle",
    "background_object",
    "partial_glass",
    "heavily_rotated",
    "bad_perspective",
    "glass_too_far",
    "glass_too_close",
}

CoordinateSpace = Literal["normalized"]


class GlassProfileAnnotationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class GlassMaskAnnotation:
    kind: Literal["polygon", "file"]
    coordinate_space: CoordinateSpace
    points: tuple[tuple[float, float], ...] | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class GlassProfileSample:
    image: str
    image_path: Path
    profile: str
    label: str
    split_group: str
    capture_session_id: str | None
    bbox_norm: tuple[float, float, float, float] | None
    keypoints_norm: dict[str, tuple[float, float, float]]
    mask: GlassMaskAnnotation | None
    true_ml: float | None = None
    level_normalized: float | None = None
    metadata: dict[str, Any] | None = None

    @property
    def is_positive(self) -> bool:
        return self.label in POSITIVE_LABELS

    @property
    def is_negative(self) -> bool:
        return self.label in NEGATIVE_LABELS

    @property
    def has_bbox(self) -> bool:
        return self.bbox_norm is not None

    @property
    def has_mask(self) -> bool:
        return self.mask is not None

    @property
    def has_required_keypoints(self) -> bool:
        return all(name in self.keypoints_norm for name in KEYPOINT_NAMES)


@dataclass(frozen=True, slots=True)
class GlassProfileAnnotationDocument:
    dataset_id: str
    dataset_version: str
    schema_version: str
    profile_key: str
    raw_dir: Path
    samples: tuple[GlassProfileSample, ...]
    notes: str | None
    source_path: Path | None = None


def load_glass_profile_annotations(
    *,
    datasets_root: Path,
    annotation_relative_path: str,
) -> GlassProfileAnnotationDocument:
    root = datasets_root.resolve()
    annotation_path = _resolve_under_root(
        root,
        annotation_relative_path,
        field_name="annotation_relative_path",
    )
    if not annotation_path.is_file():
        raise GlassProfileAnnotationError(
            f"Annotation file not found: {annotation_relative_path}"
        )

    try:
        payload = json.loads(annotation_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise GlassProfileAnnotationError("Annotation JSON is invalid.") from exc

    document = parse_glass_profile_annotations(
        datasets_root=root,
        payload=payload,
        source_path=annotation_path,
    )
    return document


def parse_glass_profile_annotations(
    *,
    datasets_root: Path,
    payload: dict[str, Any],
    source_path: Path | None = None,
) -> GlassProfileAnnotationDocument:
    if not isinstance(payload, dict):
        raise GlassProfileAnnotationError("Annotation payload must be an object.")

    # Legacy calibration packages are intentionally supported for audits only.
    # They do not contain bbox/mask/keypoint labels and are not training-ready.
    if "points" in payload and "samples" not in payload:
        return _parse_legacy_calibration_annotations(
            datasets_root=datasets_root,
            payload=payload,
            source_path=source_path,
        )

    required = ("dataset_id", "dataset_version", "raw_dir", "samples")
    for key in required:
        if key not in payload:
            raise GlassProfileAnnotationError(f"Annotation missing {key}.")

    raw_dir = _resolve_under_root(
        datasets_root.resolve(),
        str(payload["raw_dir"]),
        field_name="raw_dir",
    )
    if not raw_dir.is_dir():
        raise GlassProfileAnnotationError("raw_dir does not exist.")

    profile_key = str(payload.get("profile_key") or GLASS_500ML_PROFILE_KEY)
    samples_raw = payload["samples"]
    if not isinstance(samples_raw, list) or not samples_raw:
        raise GlassProfileAnnotationError("samples must be a non-empty list.")

    samples = tuple(
        _parse_sample(
            raw_dir=raw_dir,
            item=item,
            index=index,
            default_profile=profile_key,
        )
        for index, item in enumerate(samples_raw)
    )

    return GlassProfileAnnotationDocument(
        dataset_id=str(payload["dataset_id"]),
        dataset_version=str(payload["dataset_version"]),
        schema_version=str(
            payload.get("schema_version")
            or "glass-profile-annotation-v2"
        ),
        profile_key=profile_key,
        raw_dir=raw_dir,
        samples=samples,
        notes=payload.get("notes"),
        source_path=source_path,
    )


def _parse_legacy_calibration_annotations(
    *,
    datasets_root: Path,
    payload: dict[str, Any],
    source_path: Path | None,
) -> GlassProfileAnnotationDocument:
    required = ("dataset_id", "dataset_version", "raw_dir", "points")
    for key in required:
        if key not in payload:
            raise GlassProfileAnnotationError(f"Legacy annotation missing {key}.")

    raw_dir = _resolve_under_root(
        datasets_root.resolve(),
        str(payload["raw_dir"]),
        field_name="raw_dir",
    )
    points = payload["points"]
    if not isinstance(points, list) or not points:
        raise GlassProfileAnnotationError("points must be a non-empty list.")

    profile_key = str(payload.get("bottle_profile_key") or payload["dataset_id"])
    samples: list[GlassProfileSample] = []
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise GlassProfileAnnotationError(f"points[{index}] must be an object.")
        image = _safe_relative_filename(
            point.get("image"),
            field_name=f"points[{index}].image",
        )
        image_path = (raw_dir / image).resolve()
        if not _is_under(image_path, raw_dir) or not image_path.is_file():
            raise GlassProfileAnnotationError(
                f"Raw image missing for points[{index}]."
            )
        metadata = point.get("capture_metadata") or {}
        if not isinstance(metadata, dict):
            raise GlassProfileAnnotationError(
                f"points[{index}].capture_metadata must be an object."
            )
        true_ml = (
            float(point["true_ml"])
            if point.get("true_ml") is not None
            else None
        )
        level = (
            float(point["level_normalized"])
            if point.get("level_normalized") is not None
            else None
        )
        session_id = _optional_str(metadata.get("capture_session_id"))
        samples.append(
            GlassProfileSample(
                image=image,
                image_path=image_path,
                profile=profile_key,
                label="valid_glass",
                split_group=session_id or image,
                capture_session_id=session_id,
                bbox_norm=None,
                keypoints_norm={},
                mask=None,
                true_ml=true_ml,
                level_normalized=level,
                metadata=metadata,
            )
        )

    return GlassProfileAnnotationDocument(
        dataset_id=str(payload["dataset_id"]),
        dataset_version=str(payload["dataset_version"]),
        schema_version="legacy-calibration-v1",
        profile_key=profile_key,
        raw_dir=raw_dir,
        samples=tuple(samples),
        notes=payload.get("notes"),
        source_path=source_path,
    )


def _parse_sample(
    *,
    raw_dir: Path,
    item: Any,
    index: int,
    default_profile: str,
) -> GlassProfileSample:
    if not isinstance(item, dict):
        raise GlassProfileAnnotationError(f"samples[{index}] must be an object.")
    image = _safe_relative_filename(
        item.get("image"),
        field_name=f"samples[{index}].image",
    )
    image_path = (raw_dir / image).resolve()
    if not _is_under(image_path, raw_dir) or not image_path.is_file():
        raise GlassProfileAnnotationError(f"Raw image missing for samples[{index}].")

    label = str(item.get("label") or "").strip()
    if label not in POSITIVE_LABELS and label not in NEGATIVE_LABELS:
        raise GlassProfileAnnotationError(
            f"samples[{index}].label is not a supported glass profile label."
        )

    metadata = item.get("metadata") or item.get("capture_metadata") or {}
    if not isinstance(metadata, dict):
        raise GlassProfileAnnotationError(
            f"samples[{index}].metadata must be an object."
        )

    session_id = _optional_str(
        item.get("capture_session_id") or metadata.get("capture_session_id")
    )
    explicit_group = _optional_str(item.get("split_group"))
    split_group = explicit_group or session_id or image

    return GlassProfileSample(
        image=image,
        image_path=image_path,
        profile=str(item.get("profile") or default_profile),
        label=label,
        split_group=split_group,
        capture_session_id=session_id,
        bbox_norm=_parse_bbox(item.get("bbox"), index=index),
        keypoints_norm=_parse_keypoints(item.get("keypoints"), index=index),
        mask=_parse_mask(item.get("mask"), raw_dir=raw_dir, index=index),
        true_ml=(
            float(item["true_ml"])
            if item.get("true_ml") is not None
            else None
        ),
        level_normalized=(
            float(item["level_normalized"])
            if item.get("level_normalized") is not None
            else None
        ),
        metadata=metadata,
    )


def _parse_bbox(
    value: Any,
    *,
    index: int,
) -> tuple[float, float, float, float] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple) or len(value) != 4:
        raise GlassProfileAnnotationError(
            f"samples[{index}].bbox must be [x1, y1, x2, y2]."
        )
    x1, y1, x2, y2 = (float(v) for v in value)
    if not (0.0 <= x1 < x2 <= 1.0 and 0.0 <= y1 < y2 <= 1.0):
        raise GlassProfileAnnotationError(
            f"samples[{index}].bbox must be normalized xyxy."
        )
    return (x1, y1, x2, y2)


def _parse_keypoints(
    value: Any,
    *,
    index: int,
) -> dict[str, tuple[float, float, float]]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise GlassProfileAnnotationError(
            f"samples[{index}].keypoints must be an object."
        )

    parsed: dict[str, tuple[float, float, float]] = {}
    for name, point in value.items():
        if name not in KEYPOINT_NAMES:
            raise GlassProfileAnnotationError(
                f"samples[{index}].keypoints contains unsupported point {name}."
            )
        if not isinstance(point, list | tuple) or len(point) not in (2, 3):
            raise GlassProfileAnnotationError(
                f"samples[{index}].keypoints.{name} must be [x, y] or [x, y, v]."
            )
        x = float(point[0])
        y = float(point[1])
        visibility = float(point[2]) if len(point) == 3 else 1.0
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 and 0.0 <= visibility <= 1.0):
            raise GlassProfileAnnotationError(
                f"samples[{index}].keypoints.{name} values must be normalized."
            )
        parsed[name] = (x, y, visibility)
    return parsed


def _parse_mask(
    value: Any,
    *,
    raw_dir: Path,
    index: int,
) -> GlassMaskAnnotation | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GlassProfileAnnotationError(f"samples[{index}].mask must be an object.")

    kind = str(value.get("type") or value.get("kind") or "").strip()
    coordinate_space = str(value.get("coordinate_space") or "normalized")
    if coordinate_space != "normalized":
        raise GlassProfileAnnotationError(
            f"samples[{index}].mask.coordinate_space must be normalized."
        )

    if kind == "polygon":
        raw_points = value.get("points")
        if not isinstance(raw_points, list) or len(raw_points) < 3:
            raise GlassProfileAnnotationError(
                f"samples[{index}].mask polygon requires at least 3 points."
            )
        points = tuple(_parse_norm_xy(point, index=index) for point in raw_points)
        return GlassMaskAnnotation(
            kind="polygon",
            coordinate_space="normalized",
            points=points,
        )

    if kind == "file":
        mask_path = _safe_relative_path(
            value.get("path"),
            field_name=f"samples[{index}].mask.path",
        )
        absolute_mask = (raw_dir / mask_path).resolve()
        if not _is_under(absolute_mask, raw_dir) or not absolute_mask.is_file():
            raise GlassProfileAnnotationError(
                f"samples[{index}].mask.path does not exist."
            )
        return GlassMaskAnnotation(
            kind="file",
            coordinate_space="normalized",
            path=mask_path,
        )

    raise GlassProfileAnnotationError(
        f"samples[{index}].mask.type must be polygon or file."
    )


def _parse_norm_xy(value: Any, *, index: int) -> tuple[float, float]:
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise GlassProfileAnnotationError(
            f"samples[{index}].mask point must be [x, y]."
        )
    x = float(value[0])
    y = float(value[1])
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise GlassProfileAnnotationError(
            f"samples[{index}].mask points must be normalized."
        )
    return (x, y)


def _resolve_under_root(
    root: Path,
    relative_path: str,
    *,
    field_name: str,
) -> Path:
    relative = _safe_relative_path(relative_path, field_name=field_name)
    path = (root / relative).resolve()
    if not _is_under(path, root):
        raise GlassProfileAnnotationError(f"{field_name} escapes datasets root.")
    return path


def _safe_relative_filename(value: Any, *, field_name: str) -> str:
    relative = _safe_relative_path(value, field_name=field_name)
    if "/" in relative:
        raise GlassProfileAnnotationError(f"{field_name} must be a filename.")
    return relative


def _safe_relative_path(value: Any, *, field_name: str) -> str:
    if value is None:
        raise GlassProfileAnnotationError(f"{field_name} is required.")
    raw = str(value).replace("\\", "/").strip().lstrip("/")
    parts = [part for part in raw.split("/") if part]
    if not parts or any(part == ".." for part in parts):
        raise GlassProfileAnnotationError(f"{field_name} is not a safe path.")
    if Path(raw).is_absolute() or ":" in raw:
        raise GlassProfileAnnotationError(f"{field_name} must be relative.")
    return "/".join(parts)


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
