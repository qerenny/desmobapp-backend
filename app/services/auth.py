from __future__ import annotations

from datetime import UTC, datetime
from secrets import token_urlsafe

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
from app.db.enums import NotificationChannel, UserStatus
from app.db.models import PasswordResetToken, RefreshToken, Role, User, UserRoleAssignment
from app.schemas.auth import (
    ForgotPasswordResponse,
    LoginRequest,
    LoginResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    ResetPasswordRequest,
    UserProfile,
    UserPublic,
)
from app.services.notification import create_notification_record
from app.services.rbac import get_user_permissions_context


class AuthConflictError(Exception):
    pass


class AuthCredentialsError(Exception):
    pass


class AuthTokenError(Exception):
    pass


class AuthForbiddenError(Exception):
    pass


async def _issue_session_tokens(
    session: AsyncSession,
    *,
    user: User,
    device_info: dict | None = None,
) -> tuple[str, str]:
    global_roles, venue_roles, permissions = await get_user_permissions_context(session, user.id)
    access_token = build_access_token(
        user_id=str(user.id),
        email=user.email,
        global_roles=global_roles,
        venue_roles=venue_roles,
        permissions=permissions,
    )
    refresh_token = build_refresh_token()
    session.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh_token),
            expires_at=datetime.now(UTC) + settings.refresh_token_ttl,
            device_info=device_info or {"provider": "mock"},
        )
    )
    return access_token, refresh_token


def _serialize_user_profile(user: User) -> UserProfile:
    return UserProfile(
        id=user.id,
        email=user.email,
        name=user.name,
        phone=user.phone,
    )


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
    if user.status != UserStatus.ACTIVE:
        raise AuthForbiddenError("User is not active.")

    access_token, refresh_token = await _issue_session_tokens(session, user=user)
    await session.commit()

    return LoginResponse(
        accessToken=access_token,
        refreshToken=refresh_token,
        user=UserPublic.model_validate(user),
    )


async def refresh_user_session(session: AsyncSession, *, refresh_token: str) -> LoginResponse:
    now = datetime.now(UTC)
    refresh_token_record = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    if refresh_token_record is None:
        raise AuthTokenError("Invalid refresh token.")
    if refresh_token_record.expires_at <= now:
        refresh_token_record.revoked_at = now
        await session.commit()
        raise AuthTokenError("Refresh token has expired.")

    user = await session.get(User, refresh_token_record.user_id)
    if user is None:
        raise AuthTokenError("Invalid refresh token.")
    if user.status != UserStatus.ACTIVE:
        raise AuthForbiddenError("User is not active.")

    refresh_token_record.revoked_at = now
    access_token, new_refresh_token = await _issue_session_tokens(
        session,
        user=user,
        device_info=refresh_token_record.device_info,
    )
    await session.commit()

    return LoginResponse(
        accessToken=access_token,
        refreshToken=new_refresh_token,
        user=UserPublic.model_validate(user),
    )


async def logout_user_session(session: AsyncSession, *, refresh_token: str) -> None:
    now = datetime.now(UTC)
    refresh_token_record = await session.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_token(refresh_token),
            RefreshToken.revoked_at.is_(None),
        )
    )
    if refresh_token_record is None or refresh_token_record.expires_at <= now:
        raise AuthTokenError("Invalid refresh token.")

    refresh_token_record.revoked_at = now
    await session.commit()


async def request_password_reset(session: AsyncSession, *, email: str) -> ForgotPasswordResponse:
    user = await session.scalar(select(User).where(User.email == email.lower()))
    if user is None or user.status != UserStatus.ACTIVE:
        return ForgotPasswordResponse(message="If the account exists, password reset instructions were created.")

    now = datetime.now(UTC)
    reset_token = token_urlsafe(32)
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(reset_token),
            expires_at=now + settings.password_reset_token_ttl,
        )
    )
    await create_notification_record(
        session,
        user_id=user.id,
        template_code="password_reset_requested",
        payload={"email": user.email},
        channel=NotificationChannel.EMAIL,
    )
    await session.commit()

    return ForgotPasswordResponse(
        message="If the account exists, password reset instructions were created.",
        resetToken=reset_token if settings.app_env != "production" else None,
    )


async def reset_password(session: AsyncSession, *, payload: ResetPasswordRequest) -> None:
    now = datetime.now(UTC)
    reset_token = await session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.token_hash == hash_token(payload.token),
            PasswordResetToken.used_at.is_(None),
        )
    )
    if reset_token is None or reset_token.expires_at <= now:
        raise AuthTokenError("Invalid or expired reset token.")

    user = await session.get(User, reset_token.user_id)
    if user is None or user.status != UserStatus.ACTIVE:
        raise AuthForbiddenError("User is not active.")

    user.password_hash = hash_password(payload.newPassword)
    reset_token.used_at = now

    refresh_tokens = (
        await session.scalars(
            select(RefreshToken).where(
                RefreshToken.user_id == user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    ).all()
    for item in refresh_tokens:
        item.revoked_at = now

    await create_notification_record(
        session,
        user_id=user.id,
        template_code="password_reset_completed",
        payload={"email": user.email},
        channel=NotificationChannel.EMAIL,
    )
    await session.commit()


async def get_current_user_profile(*, current_user: User) -> UserProfile:
    return _serialize_user_profile(current_user)


async def update_current_user_profile(
    session: AsyncSession,
    *,
    current_user: User,
    payload: ProfileUpdateRequest,
) -> UserProfile:
    if payload.name is not None:
        current_user.name = payload.name
    if payload.phone is not None:
        current_user.phone = payload.phone

    await session.commit()
    await session.refresh(current_user)
    return _serialize_user_profile(current_user)
