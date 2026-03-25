from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, HoldStatus
from app.db.models import Booking, Hold, User
from app.schemas.booking import BookingCreateRequest, BookingResponse
from app.services.availability import (
    AvailabilityNotFoundError,
    AvailabilityValidationError,
    _load_conflicts,
    _overlaps,
    _resolve_booking_rule,
    _resolve_operating_hours,
    _resolve_resource,
)


class BookingConflictError(Exception):
    pass


class BookingNotFoundError(Exception):
    pass


def _ensure_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AvailabilityValidationError(f"{field_name} must include timezone information.")
    return value.astimezone(timezone.utc)


def _serialize_booking(booking: Booking) -> BookingResponse:
    return BookingResponse(
        id=booking.id,
        level=booking.level,
        status=booking.status,
        seatId=booking.seat_id,
        roomId=booking.room_id,
        venueId=booking.venue_id,
        userId=booking.user_id,
        holdId=booking.hold_id,
        startTime=booking.start_time,
        endTime=booking.end_time,
        priceAmountCents=booking.price_amount_cents,
        priceCurrency=booking.price_currency,
        createdAt=booking.created_at,
        updatedAt=booking.updated_at,
        cancelledAt=booking.cancelled_at,
    )


async def _validate_booking_window(
    session: AsyncSession,
    *,
    context,
    start_time: datetime,
    end_time: datetime,
) -> tuple[int, int, bool]:
    now = datetime.now(timezone.utc)
    if end_time <= start_time:
        raise AvailabilityValidationError("endTime must be greater than startTime.")
    if start_time <= now:
        raise AvailabilityValidationError("startTime must be in the future.")

    duration_minutes = int((end_time - start_time).total_seconds() // 60)
    booking_rule = await _resolve_booking_rule(session, context)
    requires_payment = False
    if booking_rule is not None:
        if duration_minutes < booking_rule.min_duration_minutes:
            raise AvailabilityValidationError("Requested interval is below the minimum allowed duration.")
        if duration_minutes > booking_rule.max_duration_minutes:
            raise AvailabilityValidationError("Requested interval exceeds the maximum allowed duration.")
        if start_time > now + timedelta(days=booking_rule.max_advance_days):
            raise AvailabilityValidationError("Requested interval exceeds the maximum advance booking window.")
        requires_payment = booking_rule.requires_payment

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

    return duration_minutes, 0, requires_payment


async def _validate_hold(
    session: AsyncSession,
    *,
    hold_id: UUID,
    current_user: User,
    start_time: datetime,
    end_time: datetime,
    context,
) -> Hold:
    hold = await session.scalar(select(Hold).where(Hold.id == hold_id, Hold.user_id == current_user.id))
    now = datetime.now(timezone.utc)
    if hold is None:
        raise AvailabilityValidationError("Valid holdId is required.")
    if hold.status != HoldStatus.PENDING or hold.expires_at <= now:
        raise AvailabilityValidationError("Hold is no longer active.")
    if hold.level != context.level:
        raise AvailabilityValidationError("Hold level does not match the requested booking level.")
    if (
        hold.venue_id != context.venue_id
        or hold.room_id != context.room_id
        or hold.seat_id != context.seat_id
        or hold.start_time != start_time
        or hold.end_time != end_time
    ):
        raise AvailabilityValidationError("Hold does not match the requested booking interval.")
    return hold


async def create_booking(
    session: AsyncSession,
    *,
    current_user: User,
    payload: BookingCreateRequest,
) -> BookingResponse:
    start_time = _ensure_utc(payload.startTime, field_name="startTime")
    end_time = _ensure_utc(payload.endTime, field_name="endTime")
    context = await _resolve_resource(
        session,
        level=payload.level,
        seat_id=payload.seatId,
        room_id=payload.roomId,
        venue_id=payload.venueId,
    )

    _, price_amount_cents, requires_payment = await _validate_booking_window(
        session,
        context=context,
        start_time=start_time,
        end_time=end_time,
    )

    hold: Hold | None = None
    if payload.holdId is not None:
        hold = await _validate_hold(
            session,
            hold_id=payload.holdId,
            current_user=current_user,
            start_time=start_time,
            end_time=end_time,
            context=context,
        )

    bookings, holds = await _load_conflicts(session, context, start_time, end_time)
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in bookings):
        raise BookingConflictError("Requested slot is not available.")

    blocking_holds = [item for item in holds if hold is None or item.id != hold.id]
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in blocking_holds):
        raise BookingConflictError("Requested slot is already on hold.")

    booking = Booking(
        user_id=current_user.id,
        hold_id=hold.id if hold is not None else None,
        level=context.level,
        venue_id=context.venue_id,
        room_id=context.room_id,
        seat_id=context.seat_id,
        start_time=start_time,
        end_time=end_time,
        status=BookingStatus.PENDING if requires_payment else BookingStatus.CONFIRMED,
        price_amount_cents=price_amount_cents,
        price_currency="RUB",
    )
    session.add(booking)

    if hold is not None:
        hold.status = HoldStatus.CONVERTED

    await session.commit()
    await session.refresh(booking)
    return _serialize_booking(booking)


async def get_booking(
    session: AsyncSession,
    *,
    booking_id: UUID,
    current_user: User,
) -> BookingResponse:
    booking = await session.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id))
    if booking is None:
        raise BookingNotFoundError("Booking not found.")
    return _serialize_booking(booking)


async def cancel_booking(
    session: AsyncSession,
    *,
    booking_id: UUID,
    current_user: User,
) -> None:
    booking = await session.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id))
    if booking is None:
        raise BookingNotFoundError("Booking not found.")

    if booking.status != BookingStatus.CANCELLED:
        booking.status = BookingStatus.CANCELLED
        booking.cancelled_at = datetime.now(timezone.utc)
        await session.commit()
