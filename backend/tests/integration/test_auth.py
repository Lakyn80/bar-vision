import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.security import hash_password
from app.main import app
from app.modules.businesses.models import Business
from app.modules.memberships.models import BusinessMembership
from app.modules.users.models import User
from app.modules.venues.models import Venue


@pytest.fixture
async def api_client(db_engine: AsyncEngine):
    session_factory = async_sessionmaker(
        bind=db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with db_engine.connect() as connection:
        transaction = await connection.begin()
        session = session_factory(bind=connection)

        business_a = Business(name="Business A")
        business_b = Business(name="Business B")
        session.add_all([business_a, business_b])
        await session.flush()

        user = User(
            email="manager@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Shift Manager",
            active=True,
        )
        disabled_user = User(
            email="disabled@example.com",
            password_hash=hash_password("CorrectPassword1!"),
            full_name="Disabled User",
            active=False,
        )
        session.add_all([user, disabled_user])
        await session.flush()

        session.add(
            BusinessMembership(
                user_id=user.id,
                business_id=business_a.id,
                role="manager",
            )
        )

        venue_a = Venue(
            business_id=business_a.id,
            name="Venue A",
            timezone="Europe/Prague",
        )
        venue_b = Venue(
            business_id=business_b.id,
            name="Venue B",
            timezone="UTC",
        )
        session.add_all([venue_a, venue_b])
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
            yield {
                "client": client,
                "user": user,
                "disabled_user": disabled_user,
                "venue_a": venue_a,
                "venue_b": venue_b,
            }

        app.dependency_overrides.clear()
        await session.close()
        await transaction.rollback()


async def test_login_success(api_client) -> None:
    client = api_client["client"]

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "CorrectPassword1!",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_invalid_password(api_client) -> None:
    client = api_client["client"]

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "WrongPassword",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials."


async def test_login_unknown_user(api_client) -> None:
    client = api_client["client"]

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "nobody@example.com",
            "password": "CorrectPassword1!",
        },
    )

    assert response.status_code == 401


async def test_login_disabled_user(api_client) -> None:
    client = api_client["client"]

    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "disabled@example.com",
            "password": "CorrectPassword1!",
        },
    )

    assert response.status_code == 401


async def test_protected_endpoint_without_token(api_client) -> None:
    client = api_client["client"]

    response = await client.get("/api/v1/auth/me")

    assert response.status_code == 401


async def test_protected_endpoint_with_invalid_token(api_client) -> None:
    client = api_client["client"]

    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-token"},
    )

    assert response.status_code == 401


async def test_me_and_tenant_isolation(api_client) -> None:
    client = api_client["client"]
    venue_a = api_client["venue_a"]

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "CorrectPassword1!",
        },
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "manager@example.com"

    venues = await client.get("/api/v1/venues", headers=headers)
    assert venues.status_code == 200
    payload = venues.json()
    assert len(payload) == 1
    assert payload[0]["id"] == str(venue_a.id)
    assert payload[0]["name"] == "Venue A"


async def test_refresh_flow(api_client) -> None:
    client = api_client["client"]

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "CorrectPassword1!",
        },
    )
    refresh_token = login.json()["refresh_token"]

    refreshed = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert refreshed.status_code == 200
    body = refreshed.json()
    assert body["access_token"]
    assert body["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {body['access_token']}"},
    )
    assert me.status_code == 200


async def test_refresh_rejects_access_token(api_client) -> None:
    client = api_client["client"]

    login = await client.post(
        "/api/v1/auth/login",
        json={
            "email": "manager@example.com",
            "password": "CorrectPassword1!",
        },
    )
    access_token = login.json()["access_token"]

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401
