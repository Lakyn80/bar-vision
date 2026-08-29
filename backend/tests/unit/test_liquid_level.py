from pathlib import Path

import cv2
import numpy as np
import pytest

from app.vision.liquid_level import (
    LiquidLevelError,
    detect_liquid_level,
    detect_liquid_level_from_jpeg,
)


def _synthetic_glass(*, fill_ratio: float, width: int = 200, height: int = 400) -> np.ndarray:
    """Clear-ish glass: bright walls, darker liquid below a sharp meniscus."""
    image = np.full((height, width, 3), 230, dtype=np.uint8)
    # Vessel walls
    image[:, 60:62] = (40, 40, 40)
    image[:, 138:140] = (40, 40, 40)
    meniscus = int(height * (1.0 - fill_ratio))
    image[meniscus:height, 62:138] = (70, 55, 40)
    # Strong horizontal edge at meniscus
    image[meniscus - 1 : meniscus + 2, 62:138] = (20, 20, 20)
    return image


def test_detect_liquid_near_half_fill() -> None:
    image = _synthetic_glass(fill_ratio=0.5)
    result = detect_liquid_level(
        image,
        liquid_roi_norm=(0.25, 0.15, 0.5, 0.7),
    )
    assert 0.35 <= result.liquid_level_normalized <= 0.65
    assert result.level_score > 0.1


def test_detect_liquid_higher_when_fuller() -> None:
    low = detect_liquid_level(_synthetic_glass(fill_ratio=0.3))
    high = detect_liquid_level(_synthetic_glass(fill_ratio=0.75))
    assert high.liquid_level_normalized > low.liquid_level_normalized


def test_detect_from_jpeg_bytes() -> None:
    image = _synthetic_glass(fill_ratio=0.6)
    ok, encoded = cv2.imencode(".jpg", image)
    assert ok
    result = detect_liquid_level_from_jpeg(encoded.tobytes())
    assert 0.45 <= result.liquid_level_normalized <= 0.75


def test_blank_image_fails() -> None:
    blank = np.full((100, 80, 3), 200, dtype=np.uint8)
    with pytest.raises(LiquidLevelError):
        detect_liquid_level(blank)
