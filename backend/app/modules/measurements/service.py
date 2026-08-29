from __future__ import annotations

from functools import lru_cache
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import (
    ObjectStorageError,
    build_measurement_canonical_key,
    build_measurement_debug_key,
    download_bytes,
    object_exists,
    upload_bytes,
)
from app.core.config import get_settings
from app.modules.bottles.models import BottleProfile
from app.modules.measurements.models import Measurement
from app.vision.glass_profile import (
    GLASS_500ML_PROFILE_KEY,
    GlassProfileGeometryConfig,
    GlassProfileInferenceError,
    GlassProfileInferenceUnavailable,
    OnnxGlassProfileDetector,
    validate_profile_geometry,
)
from app.vision.canonicalization import (
    CanonicalizationError,
    CanonicalizationResult,
    canonicalize_bottle_image,
    profile_from_bottle_metadata,
)
from app.vision.liquid_level import (
    LiquidLevelError,
    detect_liquid_level_from_jpeg,
)


class MeasurementAnalyzeError(Exception):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def analyze_measurement(
    session: AsyncSession,
    *,
    measurement: Measurement,
) -> Measurement:
    if not measurement.original_image_key:
        raise MeasurementAnalyzeError(
            "Measurement has no original image to analyze.",
            status_code=400,
        )

    try:
        original_payload = await download_bytes(
            measurement.original_image_key
        )
    except ObjectStorageError as exc:
        raise MeasurementAnalyzeError(
            "Original image could not be loaded from storage.",
            status_code=503,
        ) from exc

    profile = await _load_profile(session, measurement.bottle_profile_id)
    if _requires_glass_profile_gate(profile):
        _validate_glass_profile_gate(original_payload)

    try:
        if profile is not None:
            spec = profile_from_bottle_metadata(
                canonical_width=profile.canonical_width,
                canonical_height=profile.canonical_height,
                anchor_points_json=profile.anchor_points_json,
                liquid_roi_json=profile.liquid_roi_json,
                profile_name=profile.version,
            )
            result = canonicalize_bottle_image(
                original_payload,
                profile=spec,
            )
        else:
            result = canonicalize_bottle_image(original_payload)
    except CanonicalizationError as exc:
        raise MeasurementAnalyzeError(
            exc.detail,
            status_code=422,
        ) from exc

    await _persist_canonical_outputs(measurement, result)
    measurement.status = "canonicalized"
    measurement.alignment_score = result.alignment_score
    measurement.vision_version = f"{result.vision_version}+liquid-v1"

    roi = None
    if profile is not None and isinstance(profile.liquid_roi_json, dict):
        try:
            roi = (
                float(profile.liquid_roi_json["x"]),
                float(profile.liquid_roi_json["y"]),
                float(profile.liquid_roi_json["width"]),
                float(profile.liquid_roi_json["height"]),
            )
        except (KeyError, TypeError, ValueError):
            roi = None

    try:
        level = detect_liquid_level_from_jpeg(
            result.canonical_jpeg,
            liquid_roi_norm=roi,
        )
        measurement.liquid_level_normalized = level.liquid_level_normalized
        measurement.level_score = level.level_score
        measurement.status = "leveled"
    except LiquidLevelError:
        # Canonical image is still useful; level may be retried later.
        measurement.liquid_level_normalized = None
        measurement.level_score = None

    await session.flush()
    await session.refresh(measurement)
    return measurement


def _requires_glass_profile_gate(profile: BottleProfile | None) -> bool:
    if profile is None:
        return False
    return profile.version == GLASS_500ML_PROFILE_KEY


def _validate_glass_profile_gate(payload: bytes) -> None:
    settings = get_settings()
    if not settings.glass_profile_gate_enabled:
        raise MeasurementAnalyzeError(
            "glass_500ml_v1 profile gate is disabled; calibrated measurement is blocked.",
            status_code=503,
        )

    try:
        detector = _build_glass_profile_detector(
            settings.glass_profile_onnx_path,
            settings.glass_profile_metadata_path,
        )
        detection = detector.detect(payload)
        validation = validate_profile_geometry(
            detection,
            config=GlassProfileGeometryConfig.from_metadata(detector.metadata),
        )
    except GlassProfileInferenceUnavailable as exc:
        raise MeasurementAnalyzeError(
            f"glass_500ml_v1 ONNX profile model is unavailable: {exc.detail}",
            status_code=503,
        ) from exc
    except GlassProfileInferenceError as exc:
        raise MeasurementAnalyzeError(
            f"glass_500ml_v1 ONNX profile inference failed: {exc.detail}",
            status_code=422,
        ) from exc

    if not validation.ready:
        reasons = ", ".join(validation.reasons) or "not_ready"
        raise MeasurementAnalyzeError(
            f"glass_500ml_v1 profile gate rejected frame: {reasons}",
            status_code=422,
        )


@lru_cache(maxsize=4)
def _build_glass_profile_detector(
    model_path: str | None,
    metadata_path: str | None,
) -> OnnxGlassProfileDetector:
    return OnnxGlassProfileDetector(
        model_path=model_path,
        metadata_path=metadata_path,
    )


async def _load_profile(
    session: AsyncSession,
    bottle_profile_id: UUID | None,
) -> BottleProfile | None:
    if bottle_profile_id is None:
        return None
    return await session.scalar(
        select(BottleProfile).where(BottleProfile.id == bottle_profile_id)
    )


async def _persist_canonical_outputs(
    measurement: Measurement,
    result: CanonicalizationResult,
) -> None:
    measurement_id = str(measurement.id)
    canonical_key = build_measurement_canonical_key(
        measurement_id=measurement_id,
    )
    debug_key = build_measurement_debug_key(measurement_id=measurement_id)

    try:
        await upload_bytes(
            object_key=canonical_key,
            payload=result.canonical_jpeg,
            content_type="image/jpeg",
        )
        await upload_bytes(
            object_key=debug_key,
            payload=result.debug_jpeg,
            content_type="image/jpeg",
        )
    except ObjectStorageError as exc:
        raise MeasurementAnalyzeError(
            "Object storage unavailable.",
            status_code=503,
        ) from exc

    if not object_exists(canonical_key):
        raise MeasurementAnalyzeError(
            "Canonical image was not persisted.",
            status_code=503,
        )

    measurement.canonical_image_key = canonical_key
    measurement.debug_image_key = debug_key
