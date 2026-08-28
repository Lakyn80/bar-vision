import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.core.storage import object_exists
from app.main import app
from app.modules.businesses.models import Business
from app.modules.memberships.models import BusinessMembership
from app.modules.users.models import User


# Minimal JPEG SOI/EOI for MIME validation tests.
TINY_JPEG = b"\xff\xd8\xff\xd9"


@pytest.fixture
async def products_client(db_engine: AsyncEngine):
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = session_factory(bind=connection)

        business = Business(name="Božkov Venue Group")
        other_business = Business(name="Other Group")
        session.add_all([business, other_business])
        await session.flush()

        user = User(
            email="manager@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Shift Manager",
            active=True,
        )
        session.add(user)
        await session.flush()

        session.add(
            BusinessMembership(
                user_id=user.id,
                business_id=business.id,
                role="manager",
            )
        )
        await session.flush()

        async def override_get_db_session():
            try:
                yield session
                await session.flush()
            except Exception:
                await session.rollback()
                raise

        from app.core.deps import get_db_session

        app.dependency_overrides[get_db_session] = override_get_db_session

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "manager@example.com",
                    "password": "CorrectPassword1!",
                },
            )
            token = login.json()["access_token"]
            yield {
                "client": client,
                "headers": {"Authorization": f"Bearer {token}"},
                "business_id": business.id,
                "other_business_id": other_business.id,
            }

        app.dependency_overrides.clear()
        await session.close()
        await transaction.rollback()


async def test_create_product_and_bottle_profile_with_reference(
    products_client,
) -> None:
    client = products_client["client"]
    headers = products_client["headers"]
    business_id = products_client["business_id"]

    product_response = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "business_id": str(business_id),
            "name": "Božkov Tuzemský 0.7 l",
            "brand": "Božkov",
            "nominal_volume_ml": 700,
            "barcode": "8594002750123",
        },
    )
    assert product_response.status_code == 201
    product = product_response.json()
    assert product["name"] == "Božkov Tuzemský 0.7 l"

    profile_response = await client.post(
        "/api/v1/bottle-profiles",
        headers=headers,
        json={
            "product_id": product["id"],
            "version": "bozkov-700-v1",
            "canonical_width": 640,
            "canonical_height": 1280,
            "anchor_points_json": {
                "neck": [320, 80],
                "bottom": [320, 1200],
            },
            "liquid_roi_json": {
                "x": 200,
                "y": 200,
                "w": 240,
                "h": 900,
            },
        },
    )
    assert profile_response.status_code == 201
    profile = profile_response.json()
    assert profile["canonical_width"] == 640
    assert profile["anchor_points_json"]["neck"] == [320, 80]

    upload = await client.post(
        f"/api/v1/bottle-profiles/{profile['id']}/reference-image",
        headers=headers,
        files={
            "file": ("reference.jpg", TINY_JPEG, "image/jpeg"),
        },
    )
    assert upload.status_code == 200
    uploaded = upload.json()
    assert uploaded["reference_image_key"]
    assert object_exists(uploaded["reference_image_key"])


async def test_cannot_create_product_for_foreign_business(
    products_client,
) -> None:
    client = products_client["client"]
    headers = products_client["headers"]
    other_business_id = products_client["other_business_id"]

    response = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "business_id": str(other_business_id),
            "name": "Foreign Product",
            "brand": "Other",
            "nominal_volume_ml": 700,
        },
    )
    assert response.status_code == 403
