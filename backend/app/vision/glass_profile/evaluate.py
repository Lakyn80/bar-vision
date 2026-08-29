from __future__ import annotations

import json
import statistics
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

from app.vision.glass_profile.geometry import GlassProfileValidationResult


@dataclass(frozen=True, slots=True)
class ReadyGateCase:
    image: str
    expected_ready: bool
    result: GlassProfileValidationResult


@dataclass(frozen=True, slots=True)
class ReadyGateMetrics:
    samples: int
    expected_ready: int
    expected_reject: int
    false_ready: int
    false_reject: int
    false_ready_rate: float | None
    false_reject_rate: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ModelAcceptanceReport:
    model_version: str
    dataset_version: str
    test_samples: int
    segmentation_iou: float | None
    dice: float | None
    precision: float | None
    recall: float | None
    keypoint_error_px: float | None
    keypoint_error_normalized: float | None
    false_ready_rate: float | None
    false_reject_rate: float | None
    onnx_cpu_mean_ms: float | None
    onnx_cpu_median_ms: float | None
    onnx_cpu_p95_ms: float | None
    model_size_mb: float | None
    accepted_for_production: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_ready_gate(cases: Sequence[ReadyGateCase]) -> ReadyGateMetrics:
    false_ready = 0
    false_reject = 0
    expected_ready = 0
    expected_reject = 0
    for case in cases:
        if case.expected_ready:
            expected_ready += 1
            if not case.result.ready:
                false_reject += 1
        else:
            expected_reject += 1
            if case.result.ready:
                false_ready += 1
    return ReadyGateMetrics(
        samples=len(cases),
        expected_ready=expected_ready,
        expected_reject=expected_reject,
        false_ready=false_ready,
        false_reject=false_reject,
        false_ready_rate=(
            round(false_ready / expected_reject, 6)
            if expected_reject
            else None
        ),
        false_reject_rate=(
            round(false_reject / expected_ready, 6)
            if expected_ready
            else None
        ),
    )


def percentile(values: Sequence[float], percentile_value: float) -> float | None:
    if not values:
        return None
    if len(values) == 1:
        return round(values[0], 6)
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return round(ordered[lower] * (1.0 - weight) + ordered[upper] * weight, 6)


def summarize_latency_ms(values: Sequence[float]) -> dict[str, float | None]:
    if not values:
        return {"mean": None, "median": None, "p95": None}
    return {
        "mean": round(statistics.fmean(values), 6),
        "median": round(statistics.median(values), 6),
        "p95": percentile(values, 0.95),
    }


def write_acceptance_report(
    *,
    path: Path,
    report: ModelAcceptanceReport,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2) + "\n",
        encoding="utf-8",
    )
