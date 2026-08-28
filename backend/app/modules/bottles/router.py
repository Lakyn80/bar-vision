from typing import Annotated
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.core.storage import (
    ObjectStorageError,
    build_bottle_profile_reference_key,
    object_exists,
    upload_bytes,
)
from app.modules.bottles.models import BottleProfile
from app.modules.bottles.schemas import (
    BottleProfileCreate,
    BottleProfileResponse,
)
from app.modules.memberships.models import BusinessMembership
from app.modules.products.models import Product
from app.modules.users.models import User


router = APIRouter(
    prefix="/bottle-profiles",
    tags=["bottle-profiles"],
)

ALLOWED_REFERENCE_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
}
MAX_REFERENCE_IMAGE_BYTES = 10 * 1024 * 1024


async def _get_accessible_product(
    session: AsyncSession,
    *,
    user_id: UUID,
    product_id: UUID,
) -> Product:
    product = await session.scalar(
        select(Product)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(
            Product.id == product_id,
            BusinessMembership.user_id == user_id,
        )
    )
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        )
    return product


async def _get_accessible_profile(
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bottle profile not found.",
        )
    return profile


@router.post(
    "",
    response_model=BottleProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bottle_profile(
    payload: BottleProfileCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> BottleProfile:
    await _get_accessible_product(
        session,
        user_id=current_user.id,
        product_id=payload.product_id,
    )

    profile = BottleProfile(
        product_id=payload.product_id,
        version=payload.version,
        canonical_width=payload.canonical_width,
        canonical_height=payload.canonical_height,
        bottle_contour_data=payload.bottle_contour_data,
        anchor_points_json=payload.anchor_points_json,
        liquid_roi_json=payload.liquid_roi_json,
        label_mask_json=payload.label_mask_json,
        active=payload.active,
    )
    session.add(profile)
    await session.flush()
    await session.refresh(profile)
    return profile


@router.get(
    "",
    response_model=list[BottleProfileResponse],
)
async def list_bottle_profiles(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[BottleProfile]:
    result = await session.scalars(
        select(BottleProfile)
        .join(Product, Product.id == BottleProfile.product_id)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(BusinessMembership.user_id == current_user.id)
        .order_by(BottleProfile.version)
    )
    return list(result.all())


@router.post(
    "/{profile_id}/reference-image",
    response_model=BottleProfileResponse,
)
async def upload_reference_image(
    profile_id: UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    file: UploadFile = File(...),
) -> BottleProfile:
    profile = await _get_accessible_profile(
        session,
        user_id=current_user.id,
        profile_id=profile_id,
    )

    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_REFERENCE_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG reference images are supported.",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty image upload.",
        )
    if len(payload) > MAX_REFERENCE_IMAGE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image exceeds maximum allowed size.",
        )
    if payload[:2] != b"\xff\xd8":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JPEG payload.",
        )

    object_key = build_bottle_profile_reference_key(str(profile.id))

    try:
        await upload_bytes(
            object_key=object_key,
            payload=payload,
            content_type="image/jpeg",
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

    profile.reference_image_key = object_key
    await session.flush()
    await session.refresh(profile)
    return profile
