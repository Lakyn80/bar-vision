from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


class LiquidLevelError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class LiquidLevelResult:
    """
    liquid_level_normalized: 0 = empty (bottom), 1 = full (top of ROI).
    liquid_level_y: absolute pixel row in the source image (from top).
    """

    liquid_level_y: int
    liquid_level_normalized: float
    level_score: float
    roi: tuple[int, int, int, int]


def detect_liquid_level(
    image_bgr: np.ndarray,
    *,
    liquid_roi_norm: tuple[float, float, float, float] | None = None,
) -> LiquidLevelResult:
    """
    Detect horizontal liquid meniscus inside ROI using vertical gradients.

    Pipeline: ROI → contrast normalize → Sobel-Y → row energy → score peak.
    """
    if image_bgr is None or image_bgr.size == 0:
        raise LiquidLevelError("Empty image for liquid detection.")

    height, width = image_bgr.shape[:2]
    roi_norm = liquid_roi_norm or (0.28, 0.22, 0.44, 0.58)
    rx, ry, rw, rh = roi_norm
    x0 = int(np.clip(rx, 0, 1) * width)
    y0 = int(np.clip(ry, 0, 1) * height)
    x1 = int(np.clip(rx + rw, 0, 1) * width)
    y1 = int(np.clip(ry + rh, 0, 1) * height)

    if x1 - x0 < 8 or y1 - y0 < 16:
        raise LiquidLevelError("Liquid ROI is too small.")

    roi = image_bgr[y0:y1, x0:x1]
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    # Local contrast helps clear liquids / glass reflections.
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)

    sobel_y = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    energy = np.mean(np.abs(sobel_y), axis=1)

    # Suppress rim/top and bottom base spikes a bit.
    band = energy.copy()
    margin = max(2, len(band) // 12)
    band[:margin] *= 0.35
    band[-margin:] *= 0.45

    if float(np.max(band)) < 1e-3:
        raise LiquidLevelError("No liquid-level gradient found in ROI.")

    # Smooth and pick strongest horizontal candidate.
    kernel = np.ones(5, dtype=np.float32) / 5.0
    smooth = np.convolve(band, kernel, mode="same")
    peak = int(np.argmax(smooth))
    peak_score = float(smooth[peak])
    mean_score = float(np.mean(smooth) + 1e-6)
    level_score = float(np.clip(peak_score / (mean_score * 3.0), 0.0, 1.0))

    liquid_y = y0 + peak
    roi_height = max(y1 - y0, 1)
    # 0 at bottom of ROI (empty), 1 at top of ROI (full).
    liquid_level_normalized = float(
        np.clip((y1 - liquid_y) / roi_height, 0.0, 1.0)
    )

    return LiquidLevelResult(
        liquid_level_y=int(liquid_y),
        liquid_level_normalized=round(liquid_level_normalized, 4),
        level_score=round(level_score, 4),
        roi=(x0, y0, x1, y1),
    )


def detect_liquid_level_from_jpeg(
    payload: bytes,
    *,
    liquid_roi_norm: tuple[float, float, float, float] | None = None,
) -> LiquidLevelResult:
    array = np.frombuffer(payload, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise LiquidLevelError("Could not decode image for liquid detection.")
    return detect_liquid_level(image, liquid_roi_norm=liquid_roi_norm)
