from pathlib import Path

from app.vision.calibration.engine import (
    build_cylindrical_points,
    points_from_calibration_json,
    volume_from_level,
)


def test_glass_cylinder_maps_every_ml_deterministically() -> None:
    measured = [62.5, 125, 187.5, 250, 312.5, 375, 437.5, 500]
    points = build_cylindrical_points(
        nominal_volume_ml=500,
        measured_ml=measured,
    )

    # Exact anchors
    for ml in measured:
        level = ml / 500
        estimate = volume_from_level(
            level,
            points=points,
            method="cylindrical_linear",
            nominal_volume_ml=500,
        )
        assert estimate.volume_ml == ml

    # Arbitrary milliliters between pours (1 ml resolution)
    for ml in range(0, 501):
        estimate = volume_from_level(
            ml / 500,
            points=points,
            method="cylindrical_linear",
            nominal_volume_ml=500,
        )
        assert estimate.volume_ml == float(ml)
        assert estimate.method == "cylindrical_linear"


def test_glass_annotation_json_drives_cylinder_engine() -> None:
    root = Path("/datasets")
    if not root.is_dir():
        root = Path(__file__).resolve().parents[3] / "datasets"
    annotation = root / "annotations" / "glass_500ml_v1" / "v1.json"
    assert annotation.is_file()

    import json

    payload = json.loads(annotation.read_text(encoding="utf-8"))
    points, method, nominal = points_from_calibration_json(payload)
    assert method == "cylindrical_linear"
    assert nominal == 500

    # 1 ml between measured pours
    mid = volume_from_level(
        200 / 500,
        points=points,
        method=method,
        nominal_volume_ml=nominal,
    )
    assert mid.volume_ml == 200.0

    # Known pour
    pour = volume_from_level(
        0.625,
        points=points,
        method=method,
        nominal_volume_ml=nominal,
    )
    assert pour.volume_ml == 312.5


def test_pchip_is_monotonic_between_anchors() -> None:
    from app.vision.calibration.engine import CalibrationPoint

    points = [
        CalibrationPoint(0.0, 0),
        CalibrationPoint(0.25, 100),
        CalibrationPoint(0.5, 250),
        CalibrationPoint(1.0, 500),
    ]
    previous = -1.0
    for step in range(0, 101):
        level = step / 100
        estimate = volume_from_level(level, points=points, method="pchip")
        assert estimate.volume_ml >= previous
        previous = estimate.volume_ml
