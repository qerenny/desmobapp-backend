from __future__ import annotations

from pydantic import BaseModel


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
