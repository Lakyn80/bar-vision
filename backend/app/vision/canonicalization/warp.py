from __future__ import annotations

import cv2
import numpy as np

from app.vision.canonicalization.bozkov_700 import CanonicalProfileSpec
from app.vision.canonicalization.detect import BottleAnchors


def destination_quad_pixels(
    profile: CanonicalProfileSpec,
) -> np.ndarray:
    width = float(profile.canonical_width)
    height = float(profile.canonical_height)
    return np.array(
        [
            [nx * width, ny * height]
            for nx, ny in profile.destination_anchors_norm
        ],
        dtype=np.float32,
    )


def compute_homography(
    source_anchors: BottleAnchors,
    profile: CanonicalProfileSpec,
) -> np.ndarray:
    source = source_anchors.as_ndarray()
    destination = destination_quad_pixels(profile)
    matrix = cv2.getPerspectiveTransform(source, destination)
    if matrix is None or not np.isfinite(matrix).all():
        raise ValueError("Homography computation failed.")
    return matrix


def warp_to_canonical(
    image_bgr: np.ndarray,
    homography: np.ndarray,
    profile: CanonicalProfileSpec,
) -> np.ndarray:
    return cv2.warpPerspective(
        image_bgr,
        homography,
        (profile.canonical_width, profile.canonical_height),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_CONSTANT,
        borderValue=(245, 245, 245),
    )


def encode_jpeg(image_bgr: np.ndarray, *, quality: int = 92) -> bytes:
    ok, encoded = cv2.imencode(
        ".jpg",
        image_bgr,
        [int(cv2.IMWRITE_JPEG_QUALITY), quality],
    )
    if not ok:
        raise ValueError("JPEG encoding failed.")
    return encoded.tobytes()


def score_alignment(
    *,
    image_shape: tuple[int, ...],
    anchors: BottleAnchors,
    canonical_bgr: np.ndarray,
    profile: CanonicalProfileSpec,
) -> float:
    """Heuristic 0–1 score; not a calibrated accuracy metric."""
    height, width = image_shape[:2]
    image_area = float(max(height * width, 1))
    area_ratio = anchors.contour_area / image_area
    area_component = float(np.clip((area_ratio - 0.05) / 0.35, 0.0, 1.0))

    x, y, w, h = anchors.bounding_box
    aspect = h / max(w, 1)
    aspect_component = float(np.clip(1.0 - abs(aspect - 2.8) / 2.0, 0.0, 1.0))

    roi_x, roi_y, roi_w, roi_h = profile.liquid_roi_norm
    x0 = int(roi_x * profile.canonical_width)
    y0 = int(roi_y * profile.canonical_height)
    x1 = int((roi_x + roi_w) * profile.canonical_width)
    y1 = int((roi_y + roi_h) * profile.canonical_height)
    roi = canonical_bgr[y0:y1, x0:x1]
    if roi.size == 0:
        fill_component = 0.0
    else:
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        # Non-near-white pixels indicate bottle content in ROI.
        filled = float(np.mean(gray < 235))
        fill_component = float(np.clip(filled / 0.55, 0.0, 1.0))

    score = (
        0.35 * area_component
        + 0.25 * aspect_component
        + 0.40 * fill_component
    )
    return float(round(score, 4))
