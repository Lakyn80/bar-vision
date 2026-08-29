from app.vision.glass_profile.evaluate import (
    ReadyGateCase,
    evaluate_ready_gate,
)
from app.vision.glass_profile.geometry import (
    FrameQualityEvidence,
    GlassProfileDetection,
    GlassProfileGeometryConfig,
    validate_profile_geometry,
)


CONFIG = GlassProfileGeometryConfig(
    thresholds_validated=True,
    min_blur_score=10.0,
    min_exposure_score=0.40,
)


def _valid_detection(**overrides) -> GlassProfileDetection:
    data = {
        "profile": "glass_500ml_v1",
        "detected": True,
        "profile_score": 0.98,
        "bbox_norm": (0.32, 0.14, 0.68, 0.90),
        "keypoints_norm": {
            "rim_left": (0.38, 0.22, 1.0),
            "rim_right": (0.62, 0.22, 1.0),
            "bottom_left": (0.36, 0.82, 1.0),
            "bottom_right": (0.64, 0.82, 1.0),
            "rim_center": (0.50, 0.22, 1.0),
            "bottom_center": (0.50, 0.82, 1.0),
        },
        "model_version": "glass-profile-v1.0.0-test",
        "thresholds_validated": True,
    }
    data.update(overrides)
    return GlassProfileDetection(**data)


def _quality(**overrides) -> FrameQualityEvidence:
    data = {
        "blur_score": 25.0,
        "exposure_score": 0.80,
        "brightness": 120.0,
    }
    data.update(overrides)
    return FrameQualityEvidence(**data)


def test_valid_glass_pose_reaches_ready() -> None:
    result = validate_profile_geometry(
        _valid_detection(),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is True
    assert result.geometry_valid is True
    assert result.reasons == ()


def test_wrong_glass_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(profile="wrong_glass"),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "wrong_profile" in result.reasons


def test_bottle_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(profile="bottle"),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "wrong_profile" in result.reasons


def test_no_object_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(detected=False, profile="invalid", bbox_norm=None),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "not_detected" in result.reasons


def test_partial_or_cropped_glass_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(bbox_norm=(0.00, 0.14, 0.68, 0.90)),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "position_or_crop_invalid" in result.reasons


def test_excessive_rotation_is_rejected() -> None:
    keypoints = dict(_valid_detection().keypoints_norm)
    keypoints["rim_right"] = (0.62, 0.32, 1.0)
    result = validate_profile_geometry(
        _valid_detection(keypoints_norm=keypoints),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "rotation_invalid" in result.reasons


def test_excessive_perspective_is_rejected() -> None:
    keypoints = dict(_valid_detection().keypoints_norm)
    keypoints["bottom_left"] = (0.18, 0.82, 1.0)
    keypoints["bottom_right"] = (0.82, 0.82, 1.0)
    result = validate_profile_geometry(
        _valid_detection(keypoints_norm=keypoints),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "perspective_invalid" in result.reasons


def test_excessive_scale_mismatch_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(bbox_norm=(0.46, 0.30, 0.54, 0.70)),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "scale_invalid" in result.reasons


def test_blur_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(),
        config=CONFIG,
        quality=_quality(blur_score=2.0),
    )

    assert result.ready is False
    assert "quality_invalid" in result.reasons


def test_bad_exposure_is_rejected() -> None:
    result = validate_profile_geometry(
        _valid_detection(),
        config=CONFIG,
        quality=_quality(exposure_score=0.20),
    )

    assert result.ready is False
    assert "quality_invalid" in result.reasons


def test_unvalidated_model_never_reaches_ready() -> None:
    result = validate_profile_geometry(
        _valid_detection(thresholds_validated=False),
        config=CONFIG,
        quality=_quality(),
    )

    assert result.ready is False
    assert "thresholds_or_model_unvalidated" in result.reasons


def test_same_input_is_deterministic() -> None:
    detection = _valid_detection()
    first = validate_profile_geometry(detection, config=CONFIG, quality=_quality())
    second = validate_profile_geometry(detection, config=CONFIG, quality=_quality())

    assert first.to_dict() == second.to_dict()


def test_ready_gate_metrics_track_false_ready_and_false_reject() -> None:
    valid = validate_profile_geometry(
        _valid_detection(),
        config=CONFIG,
        quality=_quality(),
    )
    invalid = validate_profile_geometry(
        _valid_detection(profile="cup"),
        config=CONFIG,
        quality=_quality(),
    )

    metrics = evaluate_ready_gate(
        [
            ReadyGateCase("valid.jpg", True, valid),
            ReadyGateCase("cup.jpg", False, invalid),
        ]
    )

    assert metrics.false_ready_rate == 0
    assert metrics.false_reject_rate == 0
