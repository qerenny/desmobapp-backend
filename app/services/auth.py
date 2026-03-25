from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    build_access_token,
    build_refresh_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.db.enums import UserStatus
from app.db.models import RefreshToken, Role, User, UserRoleAssignment
from app.schemas.auth import LoginRequest, LoginResponse, RegisterRequest, UserPublic
from app.services.rbac import get_user_permissions_context


class AuthConflictError(Exception):
    pass


class AuthCredentialsError(Exception):
    pass


async def register_user(session: AsyncSession, payload: RegisterRequest) -> UserPublic:
    user = User(
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        name=payload.name,
        phone=payload.phone,
        status=UserStatus.ACTIVE,
    )
    session.add(user)
    await session.flush()

    client_role = await session.scalar(select(Role).where(Role.code == "client"))
    if client_role is not None:
        session.add(UserRoleAssignment(user_id=user.id, role_id=client_role.id, venue_id=None))

    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise AuthConflictError("User with this email already exists.") from exc

    await session.refresh(user)
    return UserPublic.model_validate(user)


async def login_user(session: AsyncSession, payload: LoginRequest) -> LoginResponse:
    stmt = select(User).where(User.email == payload.email.lower())
    user = await session.scalar(stmt)

    if user is None or not verify_password(payload.password, user.password_hash):
        raise AuthCredentialsError("Invalid email or password.")

    global_roles, venue_roles, permissions = await get_user_permissions_context(session, user.id)
    access_token = build_access_token(
        user_id=str(user.id),
        email=user.email,
        global_roles=global_roles,
        venue_roles=venue_roles,
        permissions=permissions,
    )
    refresh_token = build_refresh_token()
    refresh_token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(UTC) + settings.refresh_token_ttl,
        device_info={"provider": "mock"},
    )
    session.add(refresh_token_record)
    await session.commit()

    return LoginResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=UserPublic.model_validate(user),
    )
