from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)
    phone: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class LoginResponse(BaseModel):
    accessToken: str
    refreshToken: str
    user: UserPublic


class RefreshRequest(BaseModel):
    refreshToken: str = Field(min_length=16)


class LogoutRequest(BaseModel):
    refreshToken: str = Field(min_length=16)


class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str
    phone: str | None = None


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    phone: str | None = None

    @model_validator(mode="after")
    def validate_not_empty(self) -> ProfileUpdateRequest:
        if self.name is None and self.phone is None:
            raise ValueError("At least one field must be provided.")
        return self
