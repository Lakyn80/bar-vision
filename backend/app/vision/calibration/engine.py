from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
from scipy.interpolate import PchipInterpolator


CalibrationMethod = Literal["cylindrical_linear", "pchip"]


class CalibrationEngineError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True, slots=True)
class CalibrationPoint:
    """One ground-truth anchor: normalized liquid height → measured ml."""

    level_normalized: float
    true_ml: float


@dataclass(frozen=True, slots=True)
class VolumeEstimate:
    volume_ml: float
    level_normalized: float
    method: CalibrationMethod
    clamped: bool
    in_calibration_range: bool


def build_cylindrical_points(
    *,
    nominal_volume_ml: float,
    measured_ml: Sequence[float] | None = None,
) -> list[CalibrationPoint]:
    """
    For a straight cylinder, height fraction equals volume fraction.

    measured_ml anchors are optional; they must lie on the same linear law
    (true_ml / nominal). They document physical pours without changing the
    deterministic mapping.
    """
    if nominal_volume_ml <= 0:
        raise CalibrationEngineError("nominal_volume_ml must be > 0.")

    mls = sorted({0.0, float(nominal_volume_ml), *(float(v) for v in (measured_ml or ()))})
    points: list[CalibrationPoint] = []
    for ml in mls:
        if ml < 0 or ml > nominal_volume_ml:
            raise CalibrationEngineError(
                f"measured_ml {ml} outside [0, {nominal_volume_ml}]."
            )
        points.append(
            CalibrationPoint(
                level_normalized=ml / nominal_volume_ml,
                true_ml=ml,
            )
        )
    return points


def volume_from_level(
    level_normalized: float,
    *,
    points: Sequence[CalibrationPoint],
    method: CalibrationMethod = "pchip",
    nominal_volume_ml: float | None = None,
) -> VolumeEstimate:
    """
    Convert normalized liquid level (0 bottom → 1 full) to milliliters.

    Deterministic: same inputs always yield the same volume_ml.
    """
    if not np.isfinite(level_normalized):
        raise CalibrationEngineError("level_normalized must be finite.")

    clamped = level_normalized < 0.0 or level_normalized > 1.0
    level = float(np.clip(level_normalized, 0.0, 1.0))

    if method == "cylindrical_linear":
        if nominal_volume_ml is None or nominal_volume_ml <= 0:
            raise CalibrationEngineError(
                "cylindrical_linear requires nominal_volume_ml > 0."
            )
        volume = level * float(nominal_volume_ml)
        return VolumeEstimate(
            volume_ml=round(volume, 4),
            level_normalized=level,
            method=method,
            clamped=clamped,
            in_calibration_range=True,
        )

    if method != "pchip":
        raise CalibrationEngineError(f"Unsupported calibration method: {method}")

    if len(points) < 2:
        raise CalibrationEngineError("PCHIP requires at least 2 calibration points.")

    xs = np.array([p.level_normalized for p in points], dtype=np.float64)
    ys = np.array([p.true_ml for p in points], dtype=np.float64)
    order = np.argsort(xs)
    xs = xs[order]
    ys = ys[order]

    if np.any(np.diff(xs) <= 0):
        raise CalibrationEngineError(
            "Calibration level_normalized values must be strictly increasing."
        )
    if np.any(np.diff(ys) < 0):
        raise CalibrationEngineError(
            "Calibration true_ml values must be non-decreasing (monotonic)."
        )

    interpolator = PchipInterpolator(xs, ys, extrapolate=False)
    in_range = bool(xs[0] <= level <= xs[-1])
    if in_range:
        volume = float(interpolator(level))
    else:
        # Clamp to end anchors outside measured span.
        volume = float(ys[0] if level < xs[0] else ys[-1])

    return VolumeEstimate(
        volume_ml=round(volume, 4),
        level_normalized=level,
        method=method,
        clamped=clamped,
        in_calibration_range=in_range,
    )


def points_from_calibration_json(
    payload: dict,
) -> tuple[list[CalibrationPoint], CalibrationMethod, float | None]:
    """Parse CalibrationVersion.calibration_points_json into engine inputs."""
    method_raw = str(
        payload.get("interpolation_method")
        or payload.get("method")
        or "pchip"
    )
    if method_raw not in ("cylindrical_linear", "pchip"):
        raise CalibrationEngineError(
            f"Unsupported interpolation_method: {method_raw}"
        )
    method: CalibrationMethod = method_raw  # type: ignore[assignment]

    nominal = payload.get("nominal_volume_ml")
    nominal_f = float(nominal) if nominal is not None else None

    raw_points = payload.get("points") or []
    if not isinstance(raw_points, list):
        raise CalibrationEngineError("points must be a list.")

    points: list[CalibrationPoint] = []
    for index, item in enumerate(raw_points):
        if not isinstance(item, dict):
            raise CalibrationEngineError(f"points[{index}] must be an object.")
        if "true_ml" not in item:
            raise CalibrationEngineError(f"points[{index}] missing true_ml.")
        true_ml = float(item["true_ml"])
        if "level_normalized" in item:
            level = float(item["level_normalized"])
        elif method == "cylindrical_linear" and nominal_f:
            level = true_ml / nominal_f
        else:
            raise CalibrationEngineError(
                f"points[{index}] missing level_normalized."
            )
        points.append(
            CalibrationPoint(level_normalized=level, true_ml=true_ml)
        )

    if method == "cylindrical_linear" and nominal_f is not None:
        # Ensure 0 and full anchors exist for a complete cylinder map.
        points = build_cylindrical_points(
            nominal_volume_ml=nominal_f,
            measured_ml=[p.true_ml for p in points],
        )

    return points, method, nominal_f
