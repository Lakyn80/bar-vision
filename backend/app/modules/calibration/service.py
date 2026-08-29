from __future__ import annotations

from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.core.config import get_settings
from app.core.storage import (
    ObjectStorageError,
    build_calibration_image_key,
    object_exists,
    upload_bytes,
)
from app.modules.bottles.models import BottleProfile, CalibrationVersion
from app.modules.calibration.dataset import (
    DatasetValidationError,
    ValidatedCalibrationDataset,
    load_annotation_package,
)
from app.modules.calibration.schemas import (
    CalibrationDatasetPayload,
    CalibrationVersionCreate,
    CalibrationVersionUpdate,
    VolumeEvaluateResponse,
)
from app.modules.memberships.models import BusinessMembership
from app.modules.products.models import Product
from app.vision.calibration.engine import (
    CalibrationEngineError,
    points_from_calibration_json,
    volume_from_level,
)


class CalibrationServiceError(Exception):
    def __init__(self, detail: str, *, status_code: int = 400) -> None:
        self.detail = detail
        self.status_code = status_code
        super().__init__(detail)


async def get_accessible_profile(
    session: AsyncSession,
    *,
    user_id: UUID,
    profile_id: UUID,
) -> BottleProfile:
    profile = await session.scalar(
        select(BottleProfile)
        .join(Product, Product.id == BottleProfile.product_id)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(
            BottleProfile.id == profile_id,
            BusinessMembership.user_id == user_id,
        )
    )
    if profile is None:
        raise CalibrationServiceError(
            "Bottle profile not found.",
            status_code=404,
        )
    return profile


async def get_accessible_calibration_version(
    session: AsyncSession,
    *,
    user_id: UUID,
    calibration_version_id: UUID,
) -> CalibrationVersion:
    row = await session.scalar(
        select(CalibrationVersion)
        .join(
            BottleProfile,
            BottleProfile.id == CalibrationVersion.bottle_profile_id,
        )
        .join(Product, Product.id == BottleProfile.product_id)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(
            CalibrationVersion.id == calibration_version_id,
            BusinessMembership.user_id == user_id,
        )
    )
    if row is None:
        raise CalibrationServiceError(
            "Calibration version not found.",
            status_code=404,
        )
    return row


def _dataset_to_storage_json(
    dataset: CalibrationDatasetPayload,
) -> dict[str, Any]:
    return {
        "dataset_id": dataset.dataset_id,
        "dataset_version": dataset.dataset_version,
        "vessel": dataset.vessel,
        "nominal_volume_ml": dataset.nominal_volume_ml,
        "step_ml": dataset.step_ml,
        "interpolation_method": dataset.interpolation_method,
        "notes": dataset.notes,
        "points": [
            {
                "true_ml": point.true_ml,
                "image": point.image,
                "level_normalized": point.level_normalized,
                "image_key": point.image_key,
                "capture_metadata": point.capture_metadata,
            }
            for point in sorted(dataset.points, key=lambda item: item.true_ml)
        ],
    }


def _validated_to_storage_json(
    package: ValidatedCalibrationDataset,
    *,
    uploaded_keys: dict[str, str],
) -> dict[str, Any]:
    return {
        "dataset_id": package.dataset_id,
        "dataset_version": package.dataset_version,
        "vessel": package.vessel,
        "nominal_volume_ml": package.nominal_volume_ml,
        "step_ml": package.step_ml,
        "interpolation_method": package.interpolation_method,
        "notes": package.notes,
        "points": [
            {
                "true_ml": point["true_ml"],
                "image": point["image"],
                "level_normalized": point.get("level_normalized"),
                "image_key": uploaded_keys.get(point["image"]),
                "capture_metadata": point["capture_metadata"],
            }
            for point in package.points
        ],
    }


async def create_calibration_version(
    session: AsyncSession,
    *,
    user_id: UUID,
    payload: CalibrationVersionCreate,
) -> CalibrationVersion:
    await get_accessible_profile(
        session,
        user_id=user_id,
        profile_id=payload.bottle_profile_id,
    )
    await _ensure_version_name_unique(
        session,
        bottle_profile_id=payload.bottle_profile_id,
        version=payload.version,
    )

    row = CalibrationVersion(
        bottle_profile_id=payload.bottle_profile_id,
        version=payload.version,
        calibration_method=payload.calibration_method,
        algorithm_version=payload.algorithm_version,
        active=payload.active,
        calibration_points_json=_dataset_to_storage_json(payload.dataset),
    )
    session.add(row)
    await session.flush()
    await session.refresh(row)
    return row


async def create_calibration_version_from_dataset(
    session: AsyncSession,
    *,
    user_id: UUID,
    bottle_profile_id: UUID,
    version: str,
    calibration_method: str,
    algorithm_version: str,
    active: bool,
    annotation_relative_path: str,
) -> CalibrationVersion:
    await get_accessible_profile(
        session,
        user_id=user_id,
        profile_id=bottle_profile_id,
    )
    await _ensure_version_name_unique(
        session,
        bottle_profile_id=bottle_profile_id,
        version=version,
    )

    settings = get_settings()
    try:
        package = load_annotation_package(
            datasets_root=Path(settings.datasets_root),
            annotation_relative_path=annotation_relative_path,
        )
    except DatasetValidationError as exc:
        raise CalibrationServiceError(exc.detail, status_code=400) from exc

    row = CalibrationVersion(
        bottle_profile_id=bottle_profile_id,
        version=version,
        calibration_method=(
            package.calibration_method or calibration_method
        ),
        algorithm_version=algorithm_version,
        active=active,
        calibration_points_json={},
    )
    session.add(row)
    await session.flush()

    uploaded_keys: dict[str, str] = {}
    try:
        for point in package.points:
            image_path = Path(point["absolute_path"])
            payload_bytes = image_path.read_bytes()
            content_type = _guess_image_content_type(image_path.name)
            object_key = build_calibration_image_key(
                bottle_profile_id=str(bottle_profile_id),
                calibration_version=version,
                filename=point["image"],
            )
            await upload_bytes(
                object_key=object_key,
                payload=payload_bytes,
                content_type=content_type,
            )
            if not object_exists(object_key):
                raise CalibrationServiceError(
                    "Calibration original was not persisted.",
                    status_code=503,
                )
            uploaded_keys[point["image"]] = object_key
    except ObjectStorageError as exc:
        raise CalibrationServiceError(
            "Object storage unavailable.",
            status_code=503,
        ) from exc
    except OSError as exc:
        raise CalibrationServiceError(
            "Failed to read calibration original from dataset.",
            status_code=400,
        ) from exc

    row.calibration_points_json = _validated_to_storage_json(
        package,
        uploaded_keys=uploaded_keys,
    )
    await session.flush()
    await session.refresh(row)
    return row


async def list_calibration_versions(
    session: AsyncSession,
    *,
    user_id: UUID,
    bottle_profile_id: UUID | None = None,
) -> list[CalibrationVersion]:
    stmt = (
        select(CalibrationVersion)
        .join(
            BottleProfile,
            BottleProfile.id == CalibrationVersion.bottle_profile_id,
        )
        .join(Product, Product.id == BottleProfile.product_id)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(BusinessMembership.user_id == user_id)
        .order_by(CalibrationVersion.version)
    )
    if bottle_profile_id is not None:
        stmt = stmt.where(
            CalibrationVersion.bottle_profile_id == bottle_profile_id
        )
    result = await session.scalars(stmt)
    return list(result.all())


async def update_calibration_version(
    session: AsyncSession,
    *,
    user_id: UUID,
    calibration_version_id: UUID,
    payload: CalibrationVersionUpdate,
) -> CalibrationVersion:
    row = await get_accessible_calibration_version(
        session,
        user_id=user_id,
        calibration_version_id=calibration_version_id,
    )

    if payload.version is not None and payload.version != row.version:
        await _ensure_version_name_unique(
            session,
            bottle_profile_id=row.bottle_profile_id,
            version=payload.version,
            exclude_id=row.id,
        )
        row.version = payload.version

    if payload.calibration_method is not None:
        row.calibration_method = payload.calibration_method
    if payload.algorithm_version is not None:
        row.algorithm_version = payload.algorithm_version
    if payload.active is not None:
        row.active = payload.active
    if payload.dataset is not None:
        # Preserve existing image_key values when the same filename is kept.
        previous_keys = {
            point.get("image"): point.get("image_key")
            for point in (row.calibration_points_json or {}).get("points", [])
            if isinstance(point, dict)
        }
        merged = payload.dataset.model_copy(deep=True)
        for point in merged.points:
            if point.image_key is None:
                point.image_key = previous_keys.get(point.image)
        row.calibration_points_json = _dataset_to_storage_json(merged)

    await session.flush()
    await session.refresh(row)
    return row


async def delete_calibration_version(
    session: AsyncSession,
    *,
    user_id: UUID,
    calibration_version_id: UUID,
) -> None:
    row = await get_accessible_calibration_version(
        session,
        user_id=user_id,
        calibration_version_id=calibration_version_id,
    )
    await session.delete(row)
    await session.flush()


async def evaluate_volume(
    session: AsyncSession,
    *,
    user_id: UUID,
    calibration_version_id: UUID,
    level_normalized: float,
) -> VolumeEvaluateResponse:
    row = await get_accessible_calibration_version(
        session,
        user_id=user_id,
        calibration_version_id=calibration_version_id,
    )
    try:
        points, method, nominal = points_from_calibration_json(
            row.calibration_points_json or {}
        )
        estimate = volume_from_level(
            level_normalized,
            points=points,
            method=method,
            nominal_volume_ml=nominal,
        )
    except CalibrationEngineError as exc:
        raise CalibrationServiceError(exc.detail, status_code=400) from exc

    return VolumeEvaluateResponse(
        calibration_version_id=row.id,
        volume_ml=estimate.volume_ml,
        level_normalized=estimate.level_normalized,
        method=estimate.method,
        clamped=estimate.clamped,
        in_calibration_range=estimate.in_calibration_range,
    )


async def attach_calibration_original(
    session: AsyncSession,
    *,
    user_id: UUID,
    calibration_version_id: UUID,
    filename: str,
    payload: bytes,
    content_type: str,
) -> CalibrationVersion:
    row = await get_accessible_calibration_version(
        session,
        user_id=user_id,
        calibration_version_id=calibration_version_id,
    )
    points_doc = dict(row.calibration_points_json or {})
    points = list(points_doc.get("points") or [])
    match = next(
        (
            point
            for point in points
            if isinstance(point, dict) and point.get("image") == filename
        ),
        None,
    )
    if match is None:
        raise CalibrationServiceError(
            "Filename is not part of this calibration version.",
            status_code=400,
        )

    object_key = build_calibration_image_key(
        bottle_profile_id=str(row.bottle_profile_id),
        calibration_version=row.version,
        filename=filename,
    )
    try:
        await upload_bytes(
            object_key=object_key,
            payload=payload,
            content_type=content_type,
        )
    except ObjectStorageError as exc:
        raise CalibrationServiceError(
            "Object storage unavailable.",
            status_code=503,
        ) from exc

    if not object_exists(object_key):
        raise CalibrationServiceError(
            "Calibration original was not persisted.",
            status_code=503,
        )

    match["image_key"] = object_key
    # SQLAlchemy JSONB needs an explicit mutation flag.
    row.calibration_points_json = {
        **points_doc,
        "points": [dict(point) for point in points],
    }
    flag_modified(row, "calibration_points_json")
    await session.flush()
    await session.refresh(row)
    return row


async def _ensure_version_name_unique(
    session: AsyncSession,
    *,
    bottle_profile_id: UUID,
    version: str,
    exclude_id: UUID | None = None,
) -> None:
    stmt = select(CalibrationVersion.id).where(
        CalibrationVersion.bottle_profile_id == bottle_profile_id,
        CalibrationVersion.version == version,
    )
    if exclude_id is not None:
        stmt = stmt.where(CalibrationVersion.id != exclude_id)
    existing = await session.scalar(stmt)
    if existing is not None:
        raise CalibrationServiceError(
            "Calibration version name already exists for this profile.",
            status_code=409,
        )


def _guess_image_content_type(filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".png"):
        return "image/png"
    if lower.endswith(".webp"):
        return "image/webp"
    return "image/jpeg"
