from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt

from app.core.config import get_settings


class TokenError(Exception):
    """Raised when a JWT cannot be validated."""


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    )
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(
        password.encode("utf-8"),
        password_hash.encode("utf-8"),
    )


def create_token(
    *,
    subject: UUID,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }

    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def create_access_token(user_id: UUID) -> str:
    settings = get_settings()
    return create_token(
        subject=user_id,
        token_type="access",
        expires_delta=timedelta(
            minutes=settings.jwt_access_token_expire_minutes,
        ),
    )


def create_refresh_token(user_id: UUID) -> str:
    settings = get_settings()
    return create_token(
        subject=user_id,
        token_type="refresh",
        expires_delta=timedelta(
            days=settings.jwt_refresh_token_expire_days,
        ),
    )


def decode_token(token: str, *, expected_type: str) -> dict[str, Any]:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise TokenError("Invalid token.") from exc

    token_type = payload.get("type")
    subject = payload.get("sub")

    if token_type != expected_type:
        raise TokenError("Invalid token type.")

    if not isinstance(subject, str) or not subject:
        raise TokenError("Invalid token subject.")

    return payload
