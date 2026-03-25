from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class AccessTokenPayload(BaseModel):
    sub: UUID
    email: EmailStr
    type: str
    global_roles: list[str] = Field(default_factory=list)
    venue_roles: dict[str, list[str]] = Field(default_factory=dict)
    permissions: list[str] = Field(default_factory=list)
