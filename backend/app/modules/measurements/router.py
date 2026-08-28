from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.core.storage import (
    ObjectStorageError,
    build_measurement_original_key,
    object_exists,
    upload_bytes,
)
from app.modules.bottles.models import BottleProfile
from app.modules.memberships.models import BusinessMembership
from app.modules.measurements.image_validation import (
    ImageValidationError,
    validate_measurement_image,
)
from app.modules.measurements.models import Measurement
from app.modules.measurements.schemas import MeasurementResponse
from app.modules.measurements.service import (
    MeasurementAnalyzeError,
    analyze_measurement,
)
from app.modules.products.models import Product
from app.modules.users.models import User


router = APIRouter(
    prefix="/measurements",
    tags=["measurements"],
)


async def _resolve_optional_profile(
    session: AsyncSession,
    *,
    user_id: UUID,
    bottle_profile_id: UUID | None,
) -> BottleProfile | None:
    if bottle_profile_id is None:
        return None

    profile = await session.scalar(
        select(BottleProfile)
        .join(Product, Product.id == BottleProfile.product_id)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(
            BottleProfile.id == bottle_profile_id,
            BusinessMembership.user_id == user_id,
        )
    )
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bottle profile not found.",
        )
    return profile


@router.post(
    "/draft",
    response_model=MeasurementResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_measurement_draft(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
    bottle_profile_id: UUID | None = Form(default=None),
) -> Measurement:
    payload = await file.read()

    try:
        validated = validate_measurement_image(
            payload=payload,
            content_type=file.content_type,
            filename=file.filename,
        )
    except ImageValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.detail,
        ) from exc

    profile = await _resolve_optional_profile(
        session,
        user_id=current_user.id,
        bottle_profile_id=bottle_profile_id,
    )

    measurement = Measurement(
        status="draft",
        measurement_type="DRAFT",
        created_by=current_user.id,
        bottle_profile_id=profile.id if profile else None,
        product_id=profile.product_id if profile else None,
    )
    session.add(measurement)
    await session.flush()

    object_key = build_measurement_original_key(
        measurement_id=str(measurement.id),
        extension=validated.extension,
    )

    try:
        await upload_bytes(
            object_key=object_key,
            payload=validated.payload,
            content_type=validated.content_type,
        )
    except ObjectStorageError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Object storage unavailable.",
        ) from exc

    if not object_exists(object_key):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Uploaded object was not persisted.",
        )

    measurement.original_image_key = object_key
    measurement.status = "uploaded"
    await session.flush()
    await session.refresh(measurement)
    return measurement


@router.post(
    "/{measurement_id}/analyze",
    response_model=MeasurementResponse,
)
async def analyze_measurement_endpoint(
    measurement_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Measurement:
    measurement = await session.scalar(
        select(Measurement).where(
            Measurement.id == measurement_id,
            Measurement.created_by == current_user.id,
        )
    )
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found.",
        )

    try:
        return await analyze_measurement(session, measurement=measurement)
    except MeasurementAnalyzeError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=exc.detail,
        ) from exc


@router.get(
    "/{measurement_id}",
    response_model=MeasurementResponse,
)
async def get_measurement(
    measurement_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Measurement:
    measurement = await session.scalar(
        select(Measurement).where(
            Measurement.id == measurement_id,
            Measurement.created_by == current_user.id,
        )
    )
    if measurement is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Measurement not found.",
        )
    return measurement
