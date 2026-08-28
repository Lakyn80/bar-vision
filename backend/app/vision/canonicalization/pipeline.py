from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.vision.canonicalization.bozkov_700 import (
    BOZKOV_700_V1_PROFILE,
    VISION_VERSION,
    CanonicalProfileSpec,
)
from app.vision.canonicalization.detect import (
    BottleDetectionError,
    decode_image_bgr,
    detect_bottle_anchors,
    draw_debug_overlay,
)
from app.vision.canonicalization.warp import (
    compute_homography,
    encode_jpeg,
    score_alignment,
    warp_to_canonical,
)


class CanonicalizationError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CanonicalizationResult:
    canonical_jpeg: bytes
    debug_jpeg: bytes
    alignment_score: float
    vision_version: str
    canonical_width: int
    canonical_height: int
    source_anchors: dict[str, list[float]]
    profile_name: str


def profile_from_bottle_metadata(
    *,
    canonical_width: int | None,
    canonical_height: int | None,
    anchor_points_json: dict[str, Any] | None,
    liquid_roi_json: dict[str, Any] | None,
    profile_name: str | None = None,
) -> CanonicalProfileSpec:
    """Build a profile spec from BottleProfile fields, with Božkov defaults."""
    base = BOZKOV_700_V1_PROFILE
    width = canonical_width or base.canonical_width
    height = canonical_height or base.canonical_height

    destination = base.destination_anchors_norm
    if anchor_points_json:
        dest = anchor_points_json.get("destination")
        if isinstance(dest, dict):
            try:
                destination = (
                    _norm_point(dest["bottom_left"]),
                    _norm_point(dest["bottom_right"]),
                    _norm_point(dest["top_right"]),
                    _norm_point(dest["top_left"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise CanonicalizationError(
                    "Invalid bottle profile anchor_points_json.destination."
                ) from exc

    liquid = base.liquid_roi_norm
    if liquid_roi_json:
        try:
            liquid = (
                float(liquid_roi_json["x"]),
                float(liquid_roi_json["y"]),
                float(liquid_roi_json["width"]),
                float(liquid_roi_json["height"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise CanonicalizationError(
                "Invalid bottle profile liquid_roi_json."
            ) from exc

    return CanonicalProfileSpec(
        name=profile_name or base.name,
        canonical_width=int(width),
        canonical_height=int(height),
        destination_anchors_norm=destination,
        liquid_roi_norm=liquid,
    )


def _norm_point(value: Any) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("Point must be [x, y].")
    x = float(value[0])
    y = float(value[1])
    if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
        raise ValueError("Normalized point out of range.")
    return (x, y)


def canonicalize_bottle_image(
    payload: bytes,
    *,
    profile: CanonicalProfileSpec | None = None,
) -> CanonicalizationResult:
    """
    Crop via contour anchors, estimate pose with a homography, and warp
    into the canonical bottle frame.
    """
    active_profile = profile or BOZKOV_700_V1_PROFILE

    try:
        image = decode_image_bgr(payload)
        anchors = detect_bottle_anchors(image)
        homography = compute_homography(anchors, active_profile)
        canonical = warp_to_canonical(image, homography, active_profile)
        debug = draw_debug_overlay(image, anchors)
        alignment = score_alignment(
            image_shape=image.shape,
            anchors=anchors,
            canonical_bgr=canonical,
            profile=active_profile,
        )
        return CanonicalizationResult(
            canonical_jpeg=encode_jpeg(canonical),
            debug_jpeg=encode_jpeg(debug, quality=85),
            alignment_score=alignment,
            vision_version=VISION_VERSION,
            canonical_width=active_profile.canonical_width,
            canonical_height=active_profile.canonical_height,
            source_anchors={
                "bottom_left": list(anchors.bottom_left),
                "bottom_right": list(anchors.bottom_right),
                "top_right": list(anchors.top_right),
                "top_left": list(anchors.top_left),
            },
            profile_name=active_profile.name,
        )
    except BottleDetectionError as exc:
        raise CanonicalizationError(str(exc)) from exc
    except ValueError as exc:
        raise CanonicalizationError(str(exc)) from exc
