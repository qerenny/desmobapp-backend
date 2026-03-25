from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import HoldStatus
from app.db.models import Hold, User
from app.schemas.hold import HoldCreateRequest, HoldResponse
from app.services.availability import (
    AvailabilityValidationError,
    _load_conflicts,
    _overlaps,
    _resolve_booking_rule,
    _resolve_operating_hours,
    _resolve_resource,
)


class HoldConflictError(Exception):
    pass


class HoldNotFoundError(Exception):
    pass


def _ensure_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AvailabilityValidationError(f"{field_name} must include timezone information.")
    return value.astimezone(UTC)


def _serialize_hold(hold: Hold) -> HoldResponse:
    return HoldResponse(
        id=hold.id,
        level=hold.level,
        seatId=hold.seat_id,
        roomId=hold.room_id,
        venueId=hold.venue_id,
        userId=hold.user_id,
        startTime=hold.start_time,
        endTime=hold.end_time,
        expiresAt=hold.expires_at,
        status=hold.status.value,
        createdAt=hold.created_at,
    )


async def create_hold(
    session: AsyncSession,
    *,
    current_user: User,
    payload: HoldCreateRequest,
) -> HoldResponse:
    start_time = _ensure_utc(payload.startTime, field_name="startTime")
    end_time = _ensure_utc(payload.endTime, field_name="endTime")
    now = datetime.now(UTC)

    if end_time <= start_time:
        raise AvailabilityValidationError("endTime must be greater than startTime.")
    if start_time <= now:
        raise AvailabilityValidationError("startTime must be in the future.")

    context = await _resolve_resource(
        session,
        level=payload.level,
        seat_id=payload.seatId,
        room_id=payload.roomId,
        venue_id=payload.venueId,
    )

    duration_minutes = int((end_time - start_time).total_seconds() // 60)
    booking_rule = await _resolve_booking_rule(session, context)
    hold_ttl_seconds = 900
    if booking_rule is not None:
        if duration_minutes < booking_rule.min_duration_minutes:
            raise AvailabilityValidationError("Requested interval is below the minimum allowed duration.")
        if duration_minutes > booking_rule.max_duration_minutes:
            raise AvailabilityValidationError("Requested interval exceeds the maximum allowed duration.")
        if start_time > now + timedelta(days=booking_rule.max_advance_days):
            raise AvailabilityValidationError("Requested interval exceeds the maximum advance booking window.")
        hold_ttl_seconds = booking_rule.hold_ttl_seconds

    resource_tz = ZoneInfo(context.timezone)
    local_start = start_time.astimezone(resource_tz)
    local_end = end_time.astimezone(resource_tz)
    if local_start.date() != local_end.date():
        raise AvailabilityValidationError("Requested interval must fit within a single local day.")

    operating_hours = await _resolve_operating_hours(session, context, local_start.date())
    if operating_hours is None:
        raise AvailabilityValidationError("Resource is closed for the selected date.")

    open_time, close_time = operating_hours
    open_at = datetime.combine(local_start.date(), open_time, tzinfo=resource_tz)
    close_at = datetime.combine(local_start.date(), close_time, tzinfo=resource_tz)
    if local_start < open_at or local_end > close_at:
        raise AvailabilityValidationError("Requested interval is outside operating hours.")

    bookings, holds = await _load_conflicts(session, context, start_time, end_time)
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in bookings):
        raise HoldConflictError("Requested slot is not available.")
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in holds):
        raise HoldConflictError("Requested slot is already on hold.")

    expires_at = min(start_time, now + timedelta(seconds=hold_ttl_seconds))
    hold = Hold(
        user_id=current_user.id,
        level=context.level,
        venue_id=context.venue_id,
        room_id=context.room_id,
        seat_id=context.seat_id,
        start_time=start_time,
        end_time=end_time,
        expires_at=expires_at,
        status=HoldStatus.PENDING,
    )
    session.add(hold)
    await session.commit()
    await session.refresh(hold)
    return _serialize_hold(hold)


async def cancel_hold(
    session: AsyncSession,
    *,
    hold_id: UUID,
    current_user: User,
) -> None:
    hold = await session.scalar(select(Hold).where(Hold.id == hold_id, Hold.user_id == current_user.id))
    if hold is None:
        raise HoldNotFoundError("Hold not found.")

    if hold.status == HoldStatus.PENDING:
        hold.status = HoldStatus.CANCELLED
        await session.commit()
