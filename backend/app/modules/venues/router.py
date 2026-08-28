from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.modules.memberships.models import BusinessMembership
from app.modules.users.models import User
from app.modules.venues.models import Venue
from app.modules.venues.schemas import VenueResponse


router = APIRouter(
    prefix="/venues",
    tags=["venues"],
)


@router.get(
    "",
    response_model=list[VenueResponse],
)
async def list_venues(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[Venue]:
    result = await session.scalars(
        select(Venue)
        .join(
            BusinessMembership,
            BusinessMembership.business_id == Venue.business_id,
        )
        .where(BusinessMembership.user_id == current_user.id)
        .order_by(Venue.name)
    )

    return list(result.all())
