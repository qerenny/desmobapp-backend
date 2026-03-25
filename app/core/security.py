from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hasher = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def build_access_token(
    *,
    user_id: str,
    email: str,
    global_roles: list[str] | None = None,
    venue_roles: dict[str, list[str]] | None = None,
    permissions: list[str] | None = None,
) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "global_roles": global_roles or [],
        "venue_roles": venue_roles or {},
        "permissions": permissions or [],
        "iat": int(now.timestamp()),
        "exp": int((now + settings.access_token_ttl).timestamp()),
    }
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def build_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
