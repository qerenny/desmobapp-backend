from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserPublic
from app.services.auth import (
    AuthConflictError,
    AuthCredentialsError,
    login_user,
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
