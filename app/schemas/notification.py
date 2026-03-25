from __future__ import annotations

from pydantic import BaseModel


class NotificationPrefsUpdate(BaseModel):
    emailNotifications: bool | None = None
    pushNotifications: bool | None = None
    reminderBeforeBooking: bool | None = None
    promotionalEmails: bool | None = None


class MessageResponse(BaseModel):
    message: str
