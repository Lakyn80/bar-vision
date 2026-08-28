from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.core.storage import object_exists
from app.main import app
from app.modules.businesses.models import Business
from app.modules.memberships.models import BusinessMembership
from app.modules.users.models import User


FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rum_test.png"


@pytest.fixture
async def measurement_client(db_engine: AsyncEngine):
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = session_factory(bind=connection)

        business = Business(name="Upload Test Business")
        session.add(business)
        await session.flush()

        user = User(
            email="uploader@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Uploader",
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
                    "email": "uploader@example.com",
                    "password": "CorrectPassword1!",
                },
            )
            token = login.json()["access_token"]
            yield {
                "client": client,
                "headers": {"Authorization": f"Bearer {token}"},
            }

        app.dependency_overrides.clear()
        await session.close()
        await transaction.rollback()


async def test_upload_measurement_draft_with_rum_png(
    measurement_client,
) -> None:
    client = measurement_client["client"]
    headers = measurement_client["headers"]
    payload = FIXTURE.read_bytes()

    response = await client.post(
        "/api/v1/measurements/draft",
        headers=headers,
        files={
            "file": ("rum_test.png", payload, "image/png"),
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "uploaded"
    assert body["measurement_type"] == "DRAFT"
    assert body["original_image_key"]
    assert body["original_image_key"].endswith("/original.png")
    assert object_exists(body["original_image_key"])

    fetched = await client.get(
        f"/api/v1/measurements/{body['id']}",
        headers=headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["original_image_key"] == body["original_image_key"]


async def test_upload_rejects_unauthenticated(
    measurement_client,
) -> None:
    client = measurement_client["client"]
    payload = FIXTURE.read_bytes()

    response = await client.post(
        "/api/v1/measurements/draft",
        files={
            "file": ("rum_test.png", payload, "image/png"),
        },
    )
    assert response.status_code == 401


async def test_upload_rejects_fake_png_extension(
    measurement_client,
) -> None:
    client = measurement_client["client"]
    headers = measurement_client["headers"]

    response = await client.post(
        "/api/v1/measurements/draft",
        headers=headers,
        files={
            "file": ("fake.png", b"not-png", "image/png"),
        },
    )
    assert response.status_code == 400


async def test_analyze_measurement_creates_canonical_image(
    measurement_client,
) -> None:
    client = measurement_client["client"]
    headers = measurement_client["headers"]
    payload = FIXTURE.read_bytes()

    uploaded = await client.post(
        "/api/v1/measurements/draft",
        headers=headers,
        files={
            "file": ("rum_test.png", payload, "image/png"),
        },
    )
    assert uploaded.status_code == 201
    measurement_id = uploaded.json()["id"]

    analyzed = await client.post(
        f"/api/v1/measurements/{measurement_id}/analyze",
        headers=headers,
    )
    assert analyzed.status_code == 200
    body = analyzed.json()
    assert body["status"] == "canonicalized"
    assert body["vision_version"] == "canonicalization-v1"
    assert body["canonical_image_key"]
    assert body["canonical_image_key"].endswith("/canonical.jpg")
    assert body["debug_image_key"]
    assert body["debug_image_key"].endswith("/debug.jpg")
    assert body["alignment_score"] is not None
    assert 0.0 < body["alignment_score"] <= 1.0
    assert object_exists(body["canonical_image_key"])
    assert object_exists(body["debug_image_key"])
