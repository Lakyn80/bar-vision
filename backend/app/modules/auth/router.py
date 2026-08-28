from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db_session
from app.modules.auth.schemas import (
    CurrentUserResponse,
    LoginRequest,
    RefreshRequest,
    TokenResponse,
)
from app.modules.auth.service import (
    AuthenticationError,
    authenticate_user,
    issue_token_pair,
    refresh_token_pair,
)
from app.modules.users.models import User


router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    payload: LoginRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    try:
        user = await authenticate_user(
            session,
            email=payload.email,
            password=payload.password,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        ) from exc

    return issue_token_pair(user)


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh(
    payload: RefreshRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TokenResponse:
    try:
        return await refresh_token_pair(
            session,
            refresh_token=payload.refresh_token,
        )
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        ) from exc


@router.get(
    "/me",
    response_model=CurrentUserResponse,
)
async def me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> CurrentUserResponse:
    return CurrentUserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        active=current_user.active,
    )
