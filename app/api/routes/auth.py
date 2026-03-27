from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    UserPublic,
)
from app.schemas.common import MessageResponse
from app.services.auth import (
    AuthConflictError,
    AuthCredentialsError,
    AuthForbiddenError,
    AuthTokenError,
    login_user,
    logout_user_session,
    refresh_user_session,
    register_user,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    payload: RegisterRequest,
    session: AsyncSession = Depends(get_db_session),
) -> UserPublic:
    try:
        return await register_user(session, payload)
    except AuthConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/login", response_model=LoginResponse, summary="Authenticate user")
async def login(
    payload: LoginRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    try:
        return await login_user(session, payload)
    except AuthCredentialsError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/refresh", response_model=LoginResponse, summary="Refresh user session")
async def refresh(
    payload: RefreshRequest,
    session: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    try:
        return await refresh_user_session(session, refresh_token=payload.refreshToken)
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except AuthForbiddenError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc


@router.post("/logout", response_model=MessageResponse, summary="Revoke refresh token")
async def logout(
    payload: LogoutRequest,
    session: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    try:
        await logout_user_session(session, refresh_token=payload.refreshToken)
    except AuthTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    return MessageResponse(message="Logged out successfully.")
