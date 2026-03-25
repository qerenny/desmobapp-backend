from __future__ import annotations

from collections.abc import Callable

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import UserStatus
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.security import AccessTokenPayload

bearer_scheme = HTTPBearer(auto_error=True)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
) -> User:
    try:
        payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
        token_payload = AccessTokenPayload.model_validate(payload)
    except (jwt.InvalidTokenError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

    if token_payload.type != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token type.")

    user = await session.scalar(select(User).where(User.id == token_payload.sub))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active.")

    return user


def require_permissions(*required_permissions: str) -> Callable:
    async def dependency(
        credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    ) -> AccessTokenPayload:
        try:
            payload = jwt.decode(credentials.credentials, settings.secret_key, algorithms=["HS256"])
            token_payload = AccessTokenPayload.model_validate(payload)
        except (jwt.InvalidTokenError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token.") from exc

        if token_payload.type != "access":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token type.")

        permission_set = set(token_payload.permissions)
        missing = [permission for permission in required_permissions if permission not in permission_set]
        if missing:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permissions: {', '.join(missing)}",
            )

        return token_payload

    return dependency
