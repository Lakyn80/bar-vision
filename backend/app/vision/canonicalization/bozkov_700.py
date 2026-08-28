"""Default geometry for Božkov / 0.7 L rum-class bottles (canonicalization v1)."""

from __future__ import annotations

from dataclasses import dataclass


VISION_VERSION = "canonicalization-v1"


@dataclass(frozen=True, slots=True)
class CanonicalProfileSpec:
    """Destination frame and ROI for one bottle profile version."""

    name: str
    canonical_width: int
    canonical_height: int
    # Normalized destination quad (0–1): BL, BR, TR, TL.
    destination_anchors_norm: tuple[
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
        tuple[float, float],
    ]
    # Normalized liquid ROI: x, y, width, height.
    liquid_roi_norm: tuple[float, float, float, float]


# Destination places bottle bottom near the lower edge and neck near the top,
# with a normalized body width so later liquid ROI stays consistent.
BOZKOV_700_V1_PROFILE = CanonicalProfileSpec(
    name="bozkov_tuzemsky_700_v1",
    canonical_width=1024,
    canonical_height=2048,
    destination_anchors_norm=(
        (0.18, 0.94),  # bottom-left
        (0.82, 0.94),  # bottom-right
        (0.62, 0.10),  # top-right (neck)
        (0.38, 0.10),  # top-left (neck)
    ),
    liquid_roi_norm=(0.28, 0.28, 0.44, 0.52),
)
