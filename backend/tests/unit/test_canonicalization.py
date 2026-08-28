from pathlib import Path

import cv2
import numpy as np
import pytest

from app.vision.canonicalization import (
    BOZKOV_700_V1_PROFILE,
    CanonicalizationError,
    canonicalize_bottle_image,
)
from app.vision.canonicalization.detect import decode_image_bgr
from app.vision.canonicalization.warp import destination_quad_pixels


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rum_test.png"


def test_canonicalize_rum_fixture_produces_expected_frame() -> None:
    payload = FIXTURE.read_bytes()
    result = canonicalize_bottle_image(payload)

    assert result.canonical_width == 1024
    assert result.canonical_height == 2048
    assert result.vision_version == "canonicalization-v1"
    assert 0.0 < result.alignment_score <= 1.0
    assert result.canonical_jpeg[:2] == b"\xff\xd8"
    assert result.debug_jpeg[:2] == b"\xff\xd8"

    canonical = cv2.imdecode(
        np.frombuffer(result.canonical_jpeg, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    assert canonical is not None
    assert canonical.shape == (2048, 1024, 3)

    dest = destination_quad_pixels(BOZKOV_700_V1_PROFILE)
    bottom_y = float(np.mean(dest[0:2, 1]))
    neck_y = float(np.mean(dest[2:4, 1]))
    assert bottom_y > neck_y
    assert abs(bottom_y / 2048 - 0.94) < 0.02
    assert abs(neck_y / 2048 - 0.10) < 0.02


def test_transformed_views_map_bottom_and_neck_consistently() -> None:
    """Same bottle under mild geometric transforms → similar canonical ROI."""
    payload = FIXTURE.read_bytes()
    original = decode_image_bgr(payload)
    base = canonicalize_bottle_image(payload)

    height, width = original.shape[:2]
    center = (width / 2.0, height / 2.0)
    variants: list[np.ndarray] = [original]

    rot = cv2.getRotationMatrix2D(center, 4.0, 1.0)
    variants.append(
        cv2.warpAffine(
            original,
            rot,
            (width, height),
            borderValue=(240, 240, 240),
        )
    )

    scale = cv2.getRotationMatrix2D(center, -3.0, 0.92)
    variants.append(
        cv2.warpAffine(
            original,
            scale,
            (width, height),
            borderValue=(240, 240, 240),
        )
    )

    dest_bottom_norms: list[float] = []
    dest_neck_norms: list[float] = []
    body_width_norms: list[float] = []

    for image in variants:
        ok, encoded = cv2.imencode(".png", image)
        assert ok
        result = canonicalize_bottle_image(encoded.tobytes())
        canonical = cv2.imdecode(
            np.frombuffer(result.canonical_jpeg, dtype=np.uint8),
            cv2.IMREAD_COLOR,
        )
        assert canonical is not None

        mid_y = int(0.55 * result.canonical_height)
        row = canonical[mid_y]
        dark = np.where(np.mean(row, axis=1) < 220)[0]
        assert len(dark) > 50
        body_width_norms.append(
            float(dark[-1] - dark[0]) / result.canonical_width
        )

        dest = destination_quad_pixels(BOZKOV_700_V1_PROFILE)
        dest_neck_norms.append(
            float(np.mean(dest[2:4, 1]) / result.canonical_height)
        )
        dest_bottom_norms.append(
            float(np.mean(dest[0:2, 1]) / result.canonical_height)
        )

    assert max(dest_neck_norms) - min(dest_neck_norms) < 1e-9
    assert max(dest_bottom_norms) - min(dest_bottom_norms) < 1e-9
    assert max(body_width_norms) - min(body_width_norms) < 0.08
    assert base.alignment_score > 0.2


def test_blank_image_rejected() -> None:
    blank = np.full((400, 300, 3), 240, dtype=np.uint8)
    ok, encoded = cv2.imencode(".png", blank)
    assert ok
    with pytest.raises(CanonicalizationError):
        canonicalize_bottle_image(encoded.tobytes())
