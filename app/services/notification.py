from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import NotificationChannel, NotificationStatus
from app.db.models import Notification, NotificationDevice, NotificationPreference, User
from app.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    NotificationPreferencesResponse,
    NotificationPrefsUpdate,
    PushTokenCreateRequest,
    PushTokenResponse,
)


def _serialize_notification(notification: Notification) -> NotificationItem:
    return NotificationItem(
        id=notification.id,
        channel=notification.channel,
        templateCode=notification.template_code,
        payload=notification.payload,
        status=notification.status,
        scheduledAt=notification.scheduled_at,
        sentAt=notification.sent_at,
        errorText=notification.error_text,
        createdAt=notification.created_at,
    )


def _serialize_push_token(device: NotificationDevice) -> PushTokenResponse:
    return PushTokenResponse(
        id=device.id,
        platform=device.platform,
        pushToken=device.push_token,
        lastSeenAt=device.last_seen_at,
    )


async def get_notification_preferences(
    session: AsyncSession,
    *,
    current_user: User,
) -> NotificationPreferencesResponse:
    preference = await session.get(NotificationPreference, current_user.id)
    if preference is None:
        return NotificationPreferencesResponse(
            emailNotifications=True,
            pushNotifications=True,
            reminderBeforeBooking=True,
            promotionalEmails=False,
        )

    return NotificationPreferencesResponse(
        emailNotifications=preference.email_notifications,
        pushNotifications=preference.push_notifications,
        reminderBeforeBooking=preference.reminder_before_booking,
        promotionalEmails=preference.promotional_emails,
    )


async def update_notification_preferences(
    session: AsyncSession,
    *,
    current_user: User,
    payload: NotificationPrefsUpdate,
) -> None:
    preference = await session.get(NotificationPreference, current_user.id)
    now = datetime.now(UTC)
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


async def create_notification_record(
    session: AsyncSession,
    *,
    user_id: UUID,
    template_code: str,
    payload: dict | None = None,
    channel: NotificationChannel = NotificationChannel.PUSH,
) -> None:
    now = datetime.now(UTC)
    session.add(
        Notification(
            user_id=user_id,
            channel=channel,
            template_code=template_code,
            payload=payload,
            status=NotificationStatus.SENT,
            scheduled_at=now,
            sent_at=now,
            created_at=now,
        )
    )


async def list_notifications(
    session: AsyncSession,
    *,
    current_user: User,
    status: NotificationStatus | None,
    page: int,
    limit: int,
) -> NotificationListResponse:
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if status is not None:
        stmt = stmt.where(Notification.status == status)

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = (
        await session.scalars(
            stmt.order_by(Notification.created_at.desc()).offset((page - 1) * limit).limit(limit)
        )
    ).all()
    return NotificationListResponse(
        items=[_serialize_notification(item) for item in items],
        page=page,
        limit=limit,
        total=total,
    )


async def register_push_token(
    session: AsyncSession,
    *,
    current_user: User,
    payload: PushTokenCreateRequest,
) -> PushTokenResponse:
    device = await session.scalar(
        select(NotificationDevice).where(NotificationDevice.push_token == payload.pushToken)
    )
    now = datetime.now(UTC)
    if device is None:
        device = NotificationDevice(
            user_id=current_user.id,
            platform=payload.platform,
            push_token=payload.pushToken,
            last_seen_at=now,
        )
        session.add(device)
    else:
        device.user_id = current_user.id
        device.platform = payload.platform
        device.last_seen_at = now

    await session.commit()
    await session.refresh(device)
    return _serialize_push_token(device)


async def delete_push_token(
    session: AsyncSession,
    *,
    current_user: User,
    device_id: UUID,
) -> None:
    device = await session.scalar(
        select(NotificationDevice).where(
            NotificationDevice.id == device_id,
            NotificationDevice.user_id == current_user.id,
        )
    )
    if device is None:
        return

    await session.delete(device)
    await session.commit()
