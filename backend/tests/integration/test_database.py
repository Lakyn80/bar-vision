from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.businesses.models import Business
from app.modules.users.models import User
from app.modules.venues.models import Venue


async def test_database_round_trip(db_session: AsyncSession) -> None:
    business = Business(
        name="Integration Test Business",
    )

    db_session.add(business)
    await db_session.flush()

    venue = Venue(
        business_id=business.id,
        name="Integration Test Venue",
        timezone="Europe/Prague",
    )

    user = User(
        email="integration-test@barvision.local",
        password_hash="integration-test-hash",
        full_name="Integration Test User",
    )

    db_session.add_all(
        [
            venue,
            user,
        ]
    )

    await db_session.flush()

    stored_business = await db_session.scalar(
        select(Business).where(
            Business.id == business.id
        )
    )

    stored_venue = await db_session.scalar(
        select(Venue).where(
            Venue.id == venue.id
        )
    )

    stored_user = await db_session.scalar(
        select(User).where(
            User.id == user.id
        )
    )

    assert stored_business is not None
    assert stored_business.name == (
        "Integration Test Business"
    )

    assert stored_venue is not None
    assert stored_venue.business_id == business.id
    assert stored_venue.timezone == "Europe/Prague"

    assert stored_user is not None
    assert stored_user.email == (
        "integration-test@barvision.local"
    )
