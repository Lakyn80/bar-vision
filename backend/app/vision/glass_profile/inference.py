from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from app.vision.glass_profile.evaluate import summarize_latency_ms
from app.vision.glass_profile.geometry import (
    GlassProfileDetection,
    GlassProfileGeometryConfig,
    validate_profile_geometry,
)
from app.vision.glass_profile.schema import (
    GLASS_500ML_PROFILE_KEY,
    KEYPOINT_NAMES,
)


class GlassProfileInferenceError(Exception):
    def __init__(self, detail: str) -> None:
        self.detail = detail
        super().__init__(detail)


class GlassProfileInferenceUnavailable(GlassProfileInferenceError):
    pass


@dataclass(frozen=True, slots=True)
class OnnxBenchmarkResult:
    input_width: int
    input_height: int
    runs: int
    mean_ms: float | None
    median_ms: float | None
    p95_ms: float | None
    model_size_mb: float | None
    providers: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "input_width": self.input_width,
            "input_height": self.input_height,
            "runs": self.runs,
            "mean_ms": self.mean_ms,
            "median_ms": self.median_ms,
            "p95_ms": self.p95_ms,
            "model_size_mb": self.model_size_mb,
            "providers": list(self.providers),
        }


class OnnxGlassProfileDetector:
    def __init__(
        self,
        *,
        model_path: str | Path | None,
        metadata_path: str | Path | None = None,
        providers: list[str] | None = None,
    ) -> None:
        if model_path is None:
            raise GlassProfileInferenceUnavailable("ONNX model path is not configured.")
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise GlassProfileInferenceUnavailable(
                f"ONNX model file not found: {self.model_path}"
            )
        self.metadata_path = Path(metadata_path) if metadata_path else None
        self.metadata = _load_metadata(self.metadata_path)
        self.input_width = int(self.metadata.get("input_width") or 512)
        self.input_height = int(self.metadata.get("input_height") or 512)
        self.profile_key = str(
            self.metadata.get("profile_key") or GLASS_500ML_PROFILE_KEY
        )
        self.keypoint_names = tuple(
            self.metadata.get("keypoint_names") or KEYPOINT_NAMES
        )

        try:
            import onnxruntime
        except ImportError as exc:
            raise GlassProfileInferenceUnavailable(
                "onnxruntime is not installed in this backend environment."
            ) from exc

        session_options = onnxruntime.SessionOptions()
        session_options.intra_op_num_threads = int(
            self.metadata.get("cpu_threads") or 4
        )
        self.session = onnxruntime.InferenceSession(
            str(self.model_path),
            sess_options=session_options,
            providers=providers or ["CPUExecutionProvider"],
        )

    def detect(self, payload: bytes) -> GlassProfileDetection:
        image = _decode_image(payload)
        input_tensor = _preprocess_image(
            image,
            input_width=self.input_width,
            input_height=self.input_height,
        )
        try:
            raw_outputs = self.session.run(None, {"image": input_tensor})
        except Exception as exc:
            raise GlassProfileInferenceError("ONNX inference failed.") from exc

        outputs = _named_outputs(self.session, raw_outputs)
        logits = outputs["profile_logits"][0].astype(np.float64)
        probabilities = _softmax(logits)
        profile_score = float(probabilities[1]) if len(probabilities) > 1 else 0.0
        detected = profile_score >= float(
            self.metadata.get("min_profile_score") or 0.5
        )
        keypoint_array = outputs["keypoints"][0]
        keypoints = {
            name: (
                float(keypoint_array[index][0]),
                float(keypoint_array[index][1]),
                float(keypoint_array[index][2]),
            )
            for index, name in enumerate(self.keypoint_names)
            if index < len(keypoint_array)
        }
        bbox = tuple(
            float(v)
            for v in np.clip(outputs["bbox"][0], 0.0, 1.0).tolist()
        )
        return GlassProfileDetection(
            profile=self.profile_key if detected else "invalid",
            detected=detected,
            profile_score=round(profile_score, 6),
            bbox_norm=bbox,  # type: ignore[arg-type]
            keypoints_norm=keypoints,
            mask_score=_mask_score(outputs.get("mask_logits")),
            model_version=self.metadata.get("model_version"),
            thresholds_validated=bool(
                self.metadata.get("accepted_for_production")
                or self.metadata.get("thresholds_validated")
            ),
        )

    def benchmark_cpu(
        self,
        payload: bytes,
        *,
        warmup_runs: int = 2,
        measured_runs: int = 20,
    ) -> OnnxBenchmarkResult:
        if measured_runs <= 0:
            raise GlassProfileInferenceError("measured_runs must be > 0.")
        for _ in range(max(warmup_runs, 0)):
            self.detect(payload)
        measurements: list[float] = []
        for _ in range(measured_runs):
            started = time.perf_counter()
            self.detect(payload)
            measurements.append((time.perf_counter() - started) * 1000.0)
        summary = summarize_latency_ms(measurements)
        return OnnxBenchmarkResult(
            input_width=self.input_width,
            input_height=self.input_height,
            runs=measured_runs,
            mean_ms=summary["mean"],
            median_ms=summary["median"],
            p95_ms=summary["p95"],
            model_size_mb=(
                round(self.model_path.stat().st_size / (1024 * 1024), 6)
                if self.model_path.exists()
                else None
            ),
            providers=tuple(self.session.get_providers()),
        )

    def validate(self, payload: bytes):
        detection = self.detect(payload)
        return validate_profile_geometry(
            detection,
            config=GlassProfileGeometryConfig.from_metadata(self.metadata),
        )


def _load_metadata(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    if not path.is_file():
        raise GlassProfileInferenceUnavailable(
            f"Model metadata file not found: {path}"
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise GlassProfileInferenceUnavailable("Model metadata must be an object.")
    return payload


def _decode_image(payload: bytes) -> np.ndarray:
    image = cv2.imdecode(np.frombuffer(payload, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise GlassProfileInferenceError("Could not decode image for ONNX inference.")
    return image


def _preprocess_image(
    image_bgr: np.ndarray,
    *,
    input_width: int,
    input_height: int,
) -> np.ndarray:
    resized = cv2.resize(
        image_bgr,
        (input_width, input_height),
        interpolation=cv2.INTER_AREA,
    )
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    normalized = rgb.astype(np.float32) / 255.0
    return np.transpose(normalized, (2, 0, 1))[None, ...]


def _named_outputs(session: Any, raw_outputs: list[np.ndarray]) -> dict[str, np.ndarray]:
    names = [item.name for item in session.get_outputs()]
    return dict(zip(names, raw_outputs, strict=True))


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - np.max(logits)
    exp = np.exp(shifted)
    return exp / np.sum(exp)


def _mask_score(mask_logits: np.ndarray | None) -> float | None:
    if mask_logits is None:
        return None
    probabilities = 1.0 / (1.0 + np.exp(-mask_logits))
    return round(float(np.mean(probabilities > 0.5)), 6)
