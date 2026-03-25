from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NotificationPreference, User
from app.schemas.notification import NotificationPrefsUpdate


async def update_notification_preferences(
    session: AsyncSession,
    *,
    current_user: User,
    payload: NotificationPrefsUpdate,
) -> None:
    preference = await session.get(NotificationPreference, current_user.id)
    now = datetime.now(timezone.utc)
    if preference is None:
        preference = NotificationPreference(
            user_id=current_user.id,
            email_notifications=True,
            push_notifications=True,
            reminder_before_booking=True,
            promotional_emails=False,
            updated_at=now,
        )
        session.add(preference)

    if payload.emailNotifications is not None:
        preference.email_notifications = payload.emailNotifications
    if payload.pushNotifications is not None:
        preference.push_notifications = payload.pushNotifications
    if payload.reminderBeforeBooking is not None:
        preference.reminder_before_booking = payload.reminderBeforeBooking
    if payload.promotionalEmails is not None:
        preference.promotional_emails = payload.promotionalEmails
    preference.updated_at = now

    await session.commit()
