from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, HoldStatus
from app.db.models import Booking, Hold, User
from app.schemas.booking import (
    BookingCreateRequest,
    BookingListItem,
    BookingListResponse,
    BookingResponse,
    BookingWindowUpdateRequest,
)
from app.services.availability import (
    AvailabilityValidationError,
    _load_conflicts,
    _overlaps,
    _resolve_booking_rule,
    _resolve_operating_hours,
    _resolve_resource,
)
from app.services.notification import create_notification_record


class BookingConflictError(Exception):
    pass


class BookingNotFoundError(Exception):
    pass


def _ensure_utc(value: datetime, *, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise AvailabilityValidationError(f"{field_name} must include timezone information.")
    return value.astimezone(UTC)


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


def _serialize_booking_list_item(booking: Booking) -> BookingListItem:
    return BookingListItem(
        id=booking.id,
        status=booking.status,
        level=booking.level,
        seatId=booking.seat_id,
        roomId=booking.room_id,
        venueId=booking.venue_id,
        startTime=booking.start_time,
        endTime=booking.end_time,
        priceAmountCents=booking.price_amount_cents,
        priceCurrency=booking.price_currency,
        createdAt=booking.created_at,
        cancelledAt=booking.cancelled_at,
    )


def _resource_kwargs_for_level(booking: Booking) -> dict:
    if booking.level.value == "seat":
        return {
            "seat_id": booking.seat_id,
            "room_id": None,
            "venue_id": None,
        }
    if booking.level.value == "room":
        return {
            "seat_id": None,
            "room_id": booking.room_id,
            "venue_id": None,
        }
    return {
        "seat_id": None,
        "room_id": None,
        "venue_id": booking.venue_id,
    }


async def _validate_booking_window(
    session: AsyncSession,
    *,
    context,
    start_time: datetime,
    end_time: datetime,
) -> tuple[int, int, bool]:
    now = datetime.now(UTC)
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
    now = datetime.now(UTC)
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
    await session.flush()

    if hold is not None:
        hold.status = HoldStatus.CONVERTED

    await create_notification_record(
        session,
        user_id=current_user.id,
        template_code="booking_created",
        payload={"bookingId": str(booking.id), "level": booking.level.value},
    )
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


async def list_bookings(
    session: AsyncSession,
    *,
    current_user: User,
    status: BookingStatus | None,
    date_from: date | None,
    date_to: date | None,
    page: int,
    limit: int,
) -> BookingListResponse:
    stmt = select(Booking).where(Booking.user_id == current_user.id)
    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if date_from is not None:
        stmt = stmt.where(Booking.start_time >= datetime.combine(date_from, time.min, tzinfo=UTC))
    if date_to is not None:
        stmt = stmt.where(
            Booking.start_time < datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
        )

    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = (
        await session.scalars(
            stmt.order_by(Booking.start_time.desc()).offset((page - 1) * limit).limit(limit)
        )
    ).all()

    return BookingListResponse(
        items=[_serialize_booking_list_item(booking) for booking in items],
        page=page,
        limit=limit,
        total=total,
    )


async def list_booking_history(
    session: AsyncSession,
    *,
    current_user: User,
    page: int,
    limit: int,
) -> BookingListResponse:
    now = datetime.now(UTC)
    stmt = select(Booking).where(
        Booking.user_id == current_user.id,
        (Booking.end_time < now)
        | (Booking.status.in_([BookingStatus.CANCELLED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW])),
    )
    total = await session.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = (
        await session.scalars(
            stmt.order_by(Booking.start_time.desc()).offset((page - 1) * limit).limit(limit)
        )
    ).all()

    return BookingListResponse(
        items=[_serialize_booking_list_item(item) for item in items],
        page=page,
        limit=limit,
        total=total,
    )


async def reschedule_booking(
    session: AsyncSession,
    *,
    booking_id: UUID,
    current_user: User,
    payload: BookingWindowUpdateRequest,
) -> BookingResponse:
    booking = await session.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id))
    if booking is None:
        raise BookingNotFoundError("Booking not found.")
    if booking.status not in {BookingStatus.PENDING, BookingStatus.CONFIRMED}:
        raise AvailabilityValidationError("Booking cannot be rescheduled in its current state.")

    start_time = _ensure_utc(payload.startTime, field_name="startTime")
    end_time = _ensure_utc(payload.endTime, field_name="endTime")
    context = await _resolve_resource(
        session,
        level=booking.level,
        **_resource_kwargs_for_level(booking),
    )
    _, _, requires_payment = await _validate_booking_window(
        session,
        context=context,
        start_time=start_time,
        end_time=end_time,
    )

    bookings, holds = await _load_conflicts(session, context, start_time, end_time)
    blocking_bookings = [item for item in bookings if item.id != booking.id]
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in blocking_bookings):
        raise BookingConflictError("Requested slot is not available.")
    if any(_overlaps(start_time, end_time, item.start_time, item.end_time) for item in holds):
        raise BookingConflictError("Requested slot is already on hold.")

    booking.start_time = start_time
    booking.end_time = end_time
    booking.status = BookingStatus.PENDING if requires_payment else BookingStatus.CONFIRMED
    await create_notification_record(
        session,
        user_id=current_user.id,
        template_code="booking_rescheduled",
        payload={"bookingId": str(booking.id)},
    )
    await session.commit()
    await session.refresh(booking)
    return _serialize_booking(booking)


async def repeat_booking(
    session: AsyncSession,
    *,
    booking_id: UUID,
    current_user: User,
    payload: BookingWindowUpdateRequest,
) -> BookingResponse:
    source_booking = await session.scalar(
        select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id)
    )
    if source_booking is None:
        raise BookingNotFoundError("Booking not found.")

    return await create_booking(
        session,
        current_user=current_user,
        payload=BookingCreateRequest(
            level=source_booking.level,
            seatId=source_booking.seat_id if source_booking.level.value == "seat" else None,
            roomId=source_booking.room_id if source_booking.level.value == "room" else None,
            venueId=source_booking.venue_id if source_booking.level.value == "venue" else None,
            holdId=None,
            startTime=payload.startTime,
            endTime=payload.endTime,
        ),
    )


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
        booking.cancelled_at = datetime.now(UTC)
        await create_notification_record(
            session,
            user_id=current_user.id,
            template_code="booking_cancelled",
            payload={"bookingId": str(booking.id)},
        )
        await session.commit()
