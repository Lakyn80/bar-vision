from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.modules.auth.schemas import TokenResponse
from app.modules.users.models import User


class AuthenticationError(Exception):
    """Raised when login or refresh credentials are invalid."""


async def authenticate_user(
    session: AsyncSession,
    *,
    email: str,
    password: str,
) -> User:
    user = await session.scalar(
        select(User).where(User.email == email.lower())
    )

    if user is None:
        raise AuthenticationError("Invalid credentials.")

    if not user.active:
        raise AuthenticationError("Invalid credentials.")

    if not verify_password(password, user.password_hash):
        raise AuthenticationError("Invalid credentials.")

    return user


def issue_token_pair(user: User) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


async def refresh_token_pair(
    session: AsyncSession,
    *,
    refresh_token: str,
) -> TokenResponse:
    try:
        payload = decode_token(
            refresh_token,
            expected_type="refresh",
        )
        from uuid import UUID

        user_id = UUID(payload["sub"])
    except (TokenError, ValueError) as exc:
        raise AuthenticationError("Invalid credentials.") from exc

    user = await session.scalar(
        select(User).where(User.id == user_id)
    )

    if user is None or not user.active:
        raise AuthenticationError("Invalid credentials.")

    return issue_token_pair(user)
