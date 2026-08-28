from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True, slots=True)
class BottleAnchors:
    """Source quad in image pixel coordinates: BL, BR, TR, TL."""

    bottom_left: tuple[float, float]
    bottom_right: tuple[float, float]
    top_right: tuple[float, float]
    top_left: tuple[float, float]
    bounding_box: tuple[int, int, int, int]
    contour_area: float

    def as_ndarray(self) -> np.ndarray:
        return np.array(
            [
                self.bottom_left,
                self.bottom_right,
                self.top_right,
                self.top_left,
            ],
            dtype=np.float32,
        )


class BottleDetectionError(Exception):
    """Raised when a usable bottle silhouette cannot be found."""


def decode_image_bgr(payload: bytes) -> np.ndarray:
    array = np.frombuffer(payload, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise BottleDetectionError("Image bytes could not be decoded.")
    return image


def _largest_bottle_contour(binary: np.ndarray) -> np.ndarray:
    contours, _ = cv2.findContours(
        binary,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE,
    )
    if not contours:
        raise BottleDetectionError("No contours found in image.")

    height, width = binary.shape[:2]
    image_area = float(height * width)
    candidates: list[tuple[float, np.ndarray]] = []

    for contour in contours:
        area = float(cv2.contourArea(contour))
        if area < image_area * 0.02:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        if h < 40 or w < 20:
            continue
        aspect = h / max(w, 1)
        # Standing bottles are taller than wide.
        if aspect < 1.2 or aspect > 6.0:
            continue
        if w / width > 0.95:
            continue
        candidates.append((area, contour))

    if not candidates:
        raise BottleDetectionError(
            "No bottle-like contour found (check framing and background)."
        )

    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def _band_extrema(
    points: np.ndarray,
    *,
    y_min: float,
    y_max: float,
) -> tuple[tuple[float, float], tuple[float, float]]:
    band = points[(points[:, 1] >= y_min) & (points[:, 1] <= y_max)]
    if len(band) < 2:
        raise BottleDetectionError(
            "Insufficient contour points in bottle band."
        )
    left = band[np.argmin(band[:, 0])]
    right = band[np.argmax(band[:, 0])]
    return (
        (float(left[0]), float(left[1])),
        (float(right[0]), float(right[1])),
    )


def detect_bottle_anchors(image_bgr: np.ndarray) -> BottleAnchors:
    """Detect bottle crop anchors via silhouette contour extrema."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Light studio backgrounds: bottle is darker → INV yields white bottle.
    _, binary = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU,
    )

    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)

    contour = _largest_bottle_contour(binary)
    x, y, w, h = cv2.boundingRect(contour)
    points = contour.reshape(-1, 2).astype(np.float32)

    bottom_left, bottom_right = _band_extrema(
        points,
        y_min=y + h * 0.90,
        y_max=y + h * 1.01,
    )
    # Neck band below the cap; avoid the very top few percent.
    top_left, top_right = _band_extrema(
        points,
        y_min=y + h * 0.04,
        y_max=y + h * 0.18,
    )

    return BottleAnchors(
        bottom_left=bottom_left,
        bottom_right=bottom_right,
        top_right=top_right,
        top_left=top_left,
        bounding_box=(int(x), int(y), int(w), int(h)),
        contour_area=float(cv2.contourArea(contour)),
    )


def draw_debug_overlay(
    image_bgr: np.ndarray,
    anchors: BottleAnchors,
) -> np.ndarray:
    overlay = image_bgr.copy()
    pts = anchors.as_ndarray().astype(np.int32)
    cv2.polylines(overlay, [pts], isClosed=True, color=(0, 255, 0), thickness=3)
    x, y, w, h = anchors.bounding_box
    cv2.rectangle(overlay, (x, y), (x + w, y + h), (255, 128, 0), 2)
    for point in pts:
        cv2.circle(
            overlay,
            (int(point[0]), int(point[1])),
            8,
            (0, 0, 255),
            -1,
        )
    return overlay
