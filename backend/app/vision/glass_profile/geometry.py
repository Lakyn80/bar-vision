from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any


from app.vision.glass_profile.schema import (
    GLASS_500ML_PROFILE_KEY,
    KEYPOINT_NAMES,
)


@dataclass(frozen=True, slots=True)
class FrameQualityEvidence:
    blur_score: float | None = None
    exposure_score: float | None = None
    brightness: float | None = None


@dataclass(frozen=True, slots=True)
class GlassProfileDetection:
    profile: str
    detected: bool
    profile_score: float
    bbox_norm: tuple[float, float, float, float] | None
    keypoints_norm: dict[str, tuple[float, float, float]] = field(default_factory=dict)
    mask_score: float | None = None
    model_version: str | None = None
    thresholds_validated: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class GlassProfileGeometryConfig:
    profile_key: str = GLASS_500ML_PROFILE_KEY
    min_profile_score: float = 0.90
    min_visible_keypoint_score: float = 0.50
    min_bbox_width: float = 0.18
    max_bbox_width: float = 0.72
    min_bbox_height: float = 0.42
    max_bbox_height: float = 0.96
    min_frame_margin: float = 0.02
    target_center_x: float = 0.50
    target_center_y: float = 0.52
    max_center_offset_x: float = 0.18
    max_center_offset_y: float = 0.18
    max_rotation_degrees: float = 7.0
    max_rim_bottom_width_delta: float = 0.28
    max_side_height_delta: float = 0.18
    min_blur_score: float | None = None
    min_exposure_score: float | None = None
    thresholds_validated: bool = False

    @classmethod
    def from_metadata(cls, metadata: dict[str, Any] | None) -> "GlassProfileGeometryConfig":
        if not metadata:
            return cls()
        raw = metadata.get("geometry_thresholds") or {}
        if not isinstance(raw, dict):
            raw = {}
        accepted = bool(
            metadata.get("accepted_for_production")
            or metadata.get("thresholds_validated")
        )
        allowed = {
            "profile_key",
            "min_profile_score",
            "min_visible_keypoint_score",
            "min_bbox_width",
            "max_bbox_width",
            "min_bbox_height",
            "max_bbox_height",
            "min_frame_margin",
            "target_center_x",
            "target_center_y",
            "max_center_offset_x",
            "max_center_offset_y",
            "max_rotation_degrees",
            "max_rim_bottom_width_delta",
            "max_side_height_delta",
            "min_blur_score",
            "min_exposure_score",
        }
        values = {key: raw[key] for key in allowed if key in raw}
        return cls(
            **values,
            thresholds_validated=accepted,
        )


@dataclass(frozen=True, slots=True)
class GlassProfileValidationResult:
    profile: str
    detected: bool
    profile_score: float
    geometry_valid: bool
    position_valid: bool
    scale_valid: bool
    rotation_valid: bool
    perspective_valid: bool
    quality_valid: bool
    ready: bool
    reasons: tuple[str, ...]
    bbox_norm: tuple[float, float, float, float] | None
    keypoints_norm: dict[str, tuple[float, float, float]]
    model_version: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_profile_geometry(
    detection: GlassProfileDetection,
    *,
    config: GlassProfileGeometryConfig | None = None,
    quality: FrameQualityEvidence | None = None,
) -> GlassProfileValidationResult:
    cfg = config or GlassProfileGeometryConfig()
    quality = quality or FrameQualityEvidence()
    reasons: list[str] = []

    detected = detection.detected and detection.profile == cfg.profile_key
    if not detection.detected:
        reasons.append("not_detected")
    if detection.profile != cfg.profile_key:
        reasons.append("wrong_profile")
    if detection.profile_score < cfg.min_profile_score:
        reasons.append("low_profile_score")

    bbox = detection.bbox_norm
    scale_valid = _scale_valid(bbox, cfg)
    position_valid = _position_valid(bbox, cfg)
    if not scale_valid:
        reasons.append("scale_invalid")
    if not position_valid:
        reasons.append("position_or_crop_invalid")

    keypoints = detection.keypoints_norm
    missing_keypoints = [
        name
        for name in KEYPOINT_NAMES
        if (
            name not in keypoints
            or keypoints[name][2] < cfg.min_visible_keypoint_score
        )
    ]
    if missing_keypoints:
        reasons.append("keypoints_missing_or_low_visibility")

    rotation_valid = False
    perspective_valid = False
    if not missing_keypoints:
        rotation_valid = _rotation_degrees(keypoints) <= cfg.max_rotation_degrees
        perspective_valid = _perspective_valid(keypoints, cfg)
    if not rotation_valid:
        reasons.append("rotation_invalid")
    if not perspective_valid:
        reasons.append("perspective_invalid")

    quality_valid = _quality_valid(quality, cfg)
    if not quality_valid:
        reasons.append("quality_invalid")

    if not cfg.thresholds_validated or not detection.thresholds_validated:
        reasons.append("thresholds_or_model_unvalidated")

    geometry_valid = (
        detected
        and detection.profile_score >= cfg.min_profile_score
        and scale_valid
        and position_valid
        and not missing_keypoints
        and rotation_valid
        and perspective_valid
    )
    ready = (
        geometry_valid
        and quality_valid
        and cfg.thresholds_validated
        and detection.thresholds_validated
    )

    return GlassProfileValidationResult(
        profile=cfg.profile_key,
        detected=detected,
        profile_score=detection.profile_score,
        geometry_valid=geometry_valid,
        position_valid=position_valid,
        scale_valid=scale_valid,
        rotation_valid=rotation_valid,
        perspective_valid=perspective_valid,
        quality_valid=quality_valid,
        ready=ready,
        reasons=tuple(dict.fromkeys(reasons)),
        bbox_norm=bbox,
        keypoints_norm=keypoints,
        model_version=detection.model_version,
    )


def _scale_valid(
    bbox: tuple[float, float, float, float] | None,
    cfg: GlassProfileGeometryConfig,
) -> bool:
    if bbox is None:
        return False
    x1, y1, x2, y2 = bbox
    width = x2 - x1
    height = y2 - y1
    return (
        cfg.min_bbox_width <= width <= cfg.max_bbox_width
        and cfg.min_bbox_height <= height <= cfg.max_bbox_height
    )


def _position_valid(
    bbox: tuple[float, float, float, float] | None,
    cfg: GlassProfileGeometryConfig,
) -> bool:
    if bbox is None:
        return False
    x1, y1, x2, y2 = bbox
    if (
        x1 < cfg.min_frame_margin
        or y1 < cfg.min_frame_margin
        or x2 > 1.0 - cfg.min_frame_margin
        or y2 > 1.0 - cfg.min_frame_margin
    ):
        return False
    center_x = (x1 + x2) / 2.0
    center_y = (y1 + y2) / 2.0
    return (
        abs(center_x - cfg.target_center_x) <= cfg.max_center_offset_x
        and abs(center_y - cfg.target_center_y) <= cfg.max_center_offset_y
    )


def _quality_valid(
    quality: FrameQualityEvidence,
    cfg: GlassProfileGeometryConfig,
) -> bool:
    if cfg.min_blur_score is not None:
        if quality.blur_score is None or quality.blur_score < cfg.min_blur_score:
            return False
    if cfg.min_exposure_score is not None:
        if (
            quality.exposure_score is None
            or quality.exposure_score < cfg.min_exposure_score
        ):
            return False
    return True


def _rotation_degrees(
    keypoints: dict[str, tuple[float, float, float]],
) -> float:
    rim_angle = _line_angle_degrees(keypoints["rim_left"], keypoints["rim_right"])
    bottom_angle = _line_angle_degrees(
        keypoints["bottom_left"],
        keypoints["bottom_right"],
    )
    axis_angle = _line_angle_degrees(
        keypoints["rim_center"],
        keypoints["bottom_center"],
    )
    return max(abs(rim_angle), abs(bottom_angle), abs(abs(axis_angle) - 90.0))


def _perspective_valid(
    keypoints: dict[str, tuple[float, float, float]],
    cfg: GlassProfileGeometryConfig,
) -> bool:
    rim_width = _distance(keypoints["rim_left"], keypoints["rim_right"])
    bottom_width = _distance(keypoints["bottom_left"], keypoints["bottom_right"])
    if min(rim_width, bottom_width) <= 1e-6:
        return False
    width_delta = abs(rim_width - bottom_width) / max(rim_width, bottom_width)

    left_height = _distance(keypoints["rim_left"], keypoints["bottom_left"])
    right_height = _distance(keypoints["rim_right"], keypoints["bottom_right"])
    if min(left_height, right_height) <= 1e-6:
        return False
    side_delta = abs(left_height - right_height) / max(left_height, right_height)

    return (
        width_delta <= cfg.max_rim_bottom_width_delta
        and side_delta <= cfg.max_side_height_delta
    )


def _line_angle_degrees(
    left: tuple[float, float, float],
    right: tuple[float, float, float],
) -> float:
    return math.degrees(math.atan2(right[1] - left[1], right[0] - left[0]))


def _distance(
    p1: tuple[float, float, float],
    p2: tuple[float, float, float],
) -> float:
    return math.hypot(p2[0] - p1[0], p2[1] - p1[1])
