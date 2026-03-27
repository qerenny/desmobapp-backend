from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import NotificationChannel, NotificationStatus


class NotificationPrefsUpdate(BaseModel):
    emailNotifications: bool | None = None
    pushNotifications: bool | None = None
    reminderBeforeBooking: bool | None = None
    promotionalEmails: bool | None = None


class NotificationPreferencesResponse(BaseModel):
    emailNotifications: bool
    pushNotifications: bool
    reminderBeforeBooking: bool
    promotionalEmails: bool


class NotificationItem(BaseModel):
    id: UUID
    channel: NotificationChannel
    templateCode: str
    payload: dict | None = None
    status: NotificationStatus
    scheduledAt: datetime
    sentAt: datetime | None = None
    errorText: str | None = None
    createdAt: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationItem]
    page: int
    limit: int
    total: int


class PushTokenCreateRequest(BaseModel):
    platform: str = Field(min_length=2, max_length=32)
    pushToken: str = Field(min_length=8, max_length=512)


class PushTokenResponse(BaseModel):
    id: UUID
    platform: str
    pushToken: str
    lastSeenAt: datetime
