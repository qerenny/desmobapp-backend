from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr


class AccessTokenPayload(BaseModel):
    sub: UUID
    email: EmailStr
    type: str
    global_roles: list[str] = []
    venue_roles: dict[str, list[str]] = {}
    permissions: list[str] = []
