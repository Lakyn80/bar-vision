import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.core.storage import object_exists
from app.main import app
from app.modules.businesses.models import Business
from app.modules.memberships.models import BusinessMembership
from app.modules.users.models import User


TINY_JPEG = b"\xff\xd8\xff\xd9"


@pytest.fixture
async def calibration_client(db_engine: AsyncEngine):
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = session_factory(bind=connection)

        business = Business(name="Glass Calibration Client")
        other = Business(name="Other Client")
        session.add_all([business, other])
        await session.flush()

        user = User(
            email="calibrator@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Calibrator",
            active=True,
        )
        outsider = User(
            email="outsider@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Outsider",
            active=True,
        )
        session.add_all([user, outsider])
        await session.flush()

        session.add(
            BusinessMembership(
                user_id=user.id,
                business_id=business.id,
                role="manager",
            )
        )
        session.add(
            BusinessMembership(
                user_id=outsider.id,
                business_id=other.id,
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
                    "email": "calibrator@example.com",
                    "password": "CorrectPassword1!",
                },
            )
            outsider_login = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "outsider@example.com",
                    "password": "CorrectPassword1!",
                },
            )
            yield {
                "client": client,
                "headers": {
                    "Authorization": f"Bearer {login.json()['access_token']}"
                },
                "outsider_headers": {
                    "Authorization": (
                        f"Bearer {outsider_login.json()['access_token']}"
                    )
                },
                "business_id": business.id,
            }

        app.dependency_overrides.clear()
        await session.close()
        await transaction.rollback()


async def _create_profile(client, headers, business_id: str) -> dict:
    product = await client.post(
        "/api/v1/products",
        headers=headers,
        json={
            "business_id": str(business_id),
            "name": "Sklenice 0.5 l",
            "brand": "House Glass",
            "nominal_volume_ml": 500,
        },
    )
    assert product.status_code == 201
    profile = await client.post(
        "/api/v1/bottle-profiles",
        headers=headers,
        json={
            "product_id": product.json()["id"],
            "version": "glass-500-v1",
            "canonical_width": 1024,
            "canonical_height": 2048,
            "liquid_roi_json": {
                "x": 0.25,
                "y": 0.2,
                "width": 0.5,
                "height": 0.6,
            },
        },
    )
    assert profile.status_code == 201
    return profile.json()


async def test_calibration_version_crud_per_client_profile(
    calibration_client,
) -> None:
    client = calibration_client["client"]
    headers = calibration_client["headers"]
    business_id = calibration_client["business_id"]
    profile = await _create_profile(client, headers, business_id)

    created = await client.post(
        "/api/v1/calibration-versions",
        headers=headers,
        json={
            "bottle_profile_id": profile["id"],
            "version": "v1",
            "calibration_method": "physical_measured_pour",
            "algorithm_version": "dataset-package-v1",
            "dataset": {
                "dataset_id": "glass_500ml_v1",
                "dataset_version": "v1",
                "vessel": "glass",
                "nominal_volume_ml": 500,
                "step_ml": 62.5,
                "points": [
                    {
                        "true_ml": 62.5,
                        "image": "0062p5ml_01.jpg",
                        "capture_metadata": {"source": "manual_phone"},
                    },
                    {
                        "true_ml": 125,
                        "image": "0125ml_01.jpg",
                        "capture_metadata": {"source": "manual_phone"},
                    },
                ],
            },
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["bottle_profile_id"] == profile["id"]
    assert body["version"] == "v1"
    assert len(body["calibration_points_json"]["points"]) == 2

    upload = await client.post(
        f"/api/v1/calibration-versions/{body['id']}/originals",
        headers=headers,
        files={
            "file": ("0062p5ml_01.jpg", TINY_JPEG, "image/jpeg"),
        },
        data={"filename": "0062p5ml_01.jpg"},
    )
    assert upload.status_code == 200
    uploaded = upload.json()
    point = next(
        item
        for item in uploaded["calibration_points_json"]["points"]
        if item["image"] == "0062p5ml_01.jpg"
    )
    assert point["image_key"]
    assert object_exists(point["image_key"])

    patched = await client.patch(
        f"/api/v1/calibration-versions/{body['id']}",
        headers=headers,
        json={
            "active": False,
            "dataset": {
                "dataset_id": "glass_500ml_v1",
                "dataset_version": "v1-edit",
                "vessel": "glass",
                "nominal_volume_ml": 500,
                "step_ml": 62.5,
                "points": [
                    {
                        "true_ml": 62.5,
                        "image": "0062p5ml_01.jpg",
                        "capture_metadata": {"source": "manual_phone"},
                    },
                    {
                        "true_ml": 125,
                        "image": "0125ml_01.jpg",
                        "capture_metadata": {"note": "relabeled"},
                    },
                ],
            },
        },
    )
    assert patched.status_code == 200
    assert patched.json()["active"] is False
    patched_point = next(
        item
        for item in patched.json()["calibration_points_json"]["points"]
        if item["image"] == "0062p5ml_01.jpg"
    )
    assert patched_point["image_key"] == point["image_key"]

    listed = await client.get(
        "/api/v1/calibration-versions",
        headers=headers,
        params={"bottle_profile_id": profile["id"]},
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    deleted = await client.delete(
        f"/api/v1/calibration-versions/{body['id']}",
        headers=headers,
    )
    assert deleted.status_code == 204

    missing = await client.get(
        f"/api/v1/calibration-versions/{body['id']}",
        headers=headers,
    )
    assert missing.status_code == 404


async def test_outsider_cannot_access_foreign_calibration(
    calibration_client,
) -> None:
    client = calibration_client["client"]
    headers = calibration_client["headers"]
    outsider_headers = calibration_client["outsider_headers"]
    business_id = calibration_client["business_id"]
    profile = await _create_profile(client, headers, business_id)

    created = await client.post(
        "/api/v1/calibration-versions",
        headers=headers,
        json={
            "bottle_profile_id": profile["id"],
            "version": "v1",
            "calibration_method": "physical_measured_pour",
            "algorithm_version": "dataset-package-v1",
            "dataset": {
                "dataset_id": "glass_500ml_v1",
                "dataset_version": "v1",
                "points": [
                    {"true_ml": 62.5, "image": "a.jpg"},
                ],
            },
        },
    )
    assert created.status_code == 201
    calibration_id = created.json()["id"]

    forbidden = await client.get(
        f"/api/v1/calibration-versions/{calibration_id}",
        headers=outsider_headers,
    )
    assert forbidden.status_code == 404
