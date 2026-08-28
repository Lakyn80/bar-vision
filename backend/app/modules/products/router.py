from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.modules.memberships.models import BusinessMembership
from app.modules.products.models import Product
from app.modules.products.schemas import ProductCreate, ProductResponse
from app.modules.users.models import User


router = APIRouter(
    prefix="/products",
    tags=["products"],
)


async def _require_business_membership(
    session: AsyncSession,
    *,
    user_id: UUID,
    business_id: UUID,
) -> None:
    membership = await session.scalar(
        select(BusinessMembership).where(
            BusinessMembership.user_id == user_id,
            BusinessMembership.business_id == business_id,
        )
    )
    if membership is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed for this business.",
        )


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Product:
    await _require_business_membership(
        session,
        user_id=current_user.id,
        business_id=payload.business_id,
    )

    product = Product(
        business_id=payload.business_id,
        name=payload.name,
        brand=payload.brand,
        nominal_volume_ml=payload.nominal_volume_ml,
        barcode=payload.barcode,
        active=payload.active,
    )
    session.add(product)
    await session.flush()
    await session.refresh(product)
    return product


@router.get(
    "",
    response_model=list[ProductResponse],
)
async def list_products(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Product]:
    result = await session.scalars(
        select(Product)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Product.business_id,
        )
        .where(BusinessMembership.user_id == current_user.id)
        .order_by(Product.name)
    )
    return list(result.all())
