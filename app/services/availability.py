from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import false, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingLevel, BookingStatus, HoldStatus
from app.db.models import Booking, BookingRule, Hold, Room, RoomHour, Seat, Venue
from app.schemas.availability import AvailabilityResponse, AvailabilitySlot

DEFAULT_OPEN_TIME = time(hour=0, minute=0)
DEFAULT_CLOSE_TIME = time(hour=23, minute=59)
BLOCKING_BOOKING_STATUSES = {
    BookingStatus.PENDING,
    BookingStatus.CONFIRMED,
    BookingStatus.CHECKED_IN,
}
BLOCKING_HOLD_STATUSES = {HoldStatus.PENDING}


class AvailabilityValidationError(Exception):
    pass


class AvailabilityNotFoundError(Exception):
    pass


@dataclass
class ResourceContext:
    level: BookingLevel
    venue_id: UUID
    room_id: UUID | None
    seat_id: UUID | None
    timezone: str


def _overlaps(slot_start: datetime, slot_end: datetime, range_start: datetime, range_end: datetime) -> bool:
    return slot_start < range_end and slot_end > range_start


async def _resolve_resource(
    session: AsyncSession,
    *,
    level: BookingLevel,
    seat_id: UUID | None,
    room_id: UUID | None,
    venue_id: UUID | None,
) -> ResourceContext:
    if level == BookingLevel.SEAT:
        if seat_id is None or room_id is not None or venue_id is not None:
            raise AvailabilityValidationError("For level=seat you must provide only seatId.")
        seat = await session.get(Seat, seat_id)
        if seat is None:
            raise AvailabilityNotFoundError("Seat not found.")
        room = await session.get(Room, seat.room_id)
        venue = await session.get(Venue, room.venue_id) if room is not None else None
        if room is None or venue is None:
            raise AvailabilityNotFoundError("Seat hierarchy is broken.")
        return ResourceContext(level=level, venue_id=venue.id, room_id=room.id, seat_id=seat.id, timezone=venue.timezone)

    if level == BookingLevel.ROOM:
        if room_id is None or seat_id is not None or venue_id is not None:
            raise AvailabilityValidationError("For level=room you must provide only roomId.")
        room = await session.get(Room, room_id)
        if room is None:
            raise AvailabilityNotFoundError("Room not found.")
        venue = await session.get(Venue, room.venue_id)
        if venue is None:
            raise AvailabilityNotFoundError("Room hierarchy is broken.")
        return ResourceContext(level=level, venue_id=venue.id, room_id=room.id, seat_id=None, timezone=venue.timezone)

    if level == BookingLevel.VENUE:
        if venue_id is None or seat_id is not None or room_id is not None:
            raise AvailabilityValidationError("For level=venue you must provide only venueId.")
        venue = await session.get(Venue, venue_id)
        if venue is None:
            raise AvailabilityNotFoundError("Venue not found.")
        return ResourceContext(level=level, venue_id=venue.id, room_id=None, seat_id=None, timezone=venue.timezone)

    raise AvailabilityValidationError("Unsupported booking level.")


async def _resolve_booking_rule(
    session: AsyncSession,
    context: ResourceContext,
) -> BookingRule | None:
    if context.level == BookingLevel.SEAT and context.room_id is not None:
        room_rule = await session.scalar(select(BookingRule).where(BookingRule.room_id == context.room_id))
        if room_rule is not None:
            return room_rule
    if context.level == BookingLevel.ROOM and context.room_id is not None:
        room_rule = await session.scalar(select(BookingRule).where(BookingRule.room_id == context.room_id))
        if room_rule is not None:
            return room_rule
    return await session.scalar(select(BookingRule).where(BookingRule.venue_id == context.venue_id))


async def _resolve_operating_hours(
    session: AsyncSession,
    context: ResourceContext,
    target_date: date,
) -> tuple[time, time] | None:
    if context.room_id is None:
        return DEFAULT_OPEN_TIME, DEFAULT_CLOSE_TIME

    room_hour = await session.scalar(
        select(RoomHour).where(RoomHour.room_id == context.room_id, RoomHour.weekday == target_date.weekday())
    )
    if room_hour is None:
        return DEFAULT_OPEN_TIME, DEFAULT_CLOSE_TIME
    if room_hour.is_closed:
        return None

    return room_hour.start_local_time or DEFAULT_OPEN_TIME, room_hour.end_local_time or DEFAULT_CLOSE_TIME


async def _load_conflicts(
    session: AsyncSession,
    context: ResourceContext,
    range_start: datetime,
    range_end: datetime,
) -> tuple[list[Booking], list[Hold]]:
    blocking_booking_query = select(Booking).where(
        Booking.status.in_(BLOCKING_BOOKING_STATUSES),
        Booking.start_time < range_end,
        Booking.end_time > range_start,
    )
    blocking_hold_query = select(Hold).where(
        Hold.status.in_(BLOCKING_HOLD_STATUSES),
        Hold.expires_at > datetime.now(timezone.utc),
        Hold.start_time < range_end,
        Hold.end_time > range_start,
    )

    if context.level == BookingLevel.SEAT:
        assert context.seat_id is not None and context.room_id is not None
        booking_filter = or_(
            Booking.seat_id == context.seat_id,
            Booking.room_id == context.room_id,
            Booking.venue_id == context.venue_id,
        )
        hold_filter = or_(
            Hold.seat_id == context.seat_id,
            Hold.room_id == context.room_id,
            Hold.venue_id == context.venue_id,
        )
    elif context.level == BookingLevel.ROOM:
        assert context.room_id is not None
        seat_ids = (
            await session.scalars(select(Seat.id).where(Seat.room_id == context.room_id))
        ).all()
        booking_filter = or_(
            Booking.room_id == context.room_id,
            Booking.venue_id == context.venue_id,
            Booking.seat_id.in_(seat_ids) if seat_ids else false(),
        )
        hold_filter = or_(
            Hold.room_id == context.room_id,
            Hold.venue_id == context.venue_id,
            Hold.seat_id.in_(seat_ids) if seat_ids else false(),
        )
    else:
        room_ids = (await session.scalars(select(Room.id).where(Room.venue_id == context.venue_id))).all()
        seat_ids = (await session.scalars(select(Seat.id).where(Seat.room_id.in_(room_ids)))).all() if room_ids else []
        booking_filter = or_(
            Booking.venue_id == context.venue_id,
            Booking.room_id.in_(room_ids) if room_ids else false(),
            Booking.seat_id.in_(seat_ids) if seat_ids else false(),
        )
        hold_filter = or_(
            Hold.venue_id == context.venue_id,
            Hold.room_id.in_(room_ids) if room_ids else false(),
            Hold.seat_id.in_(seat_ids) if seat_ids else false(),
        )

    bookings = (await session.scalars(blocking_booking_query.where(booking_filter))).all()
    holds = (await session.scalars(blocking_hold_query.where(hold_filter))).all()
    return bookings, holds


async def get_availability(
    session: AsyncSession,
    *,
    level: BookingLevel,
    seat_id: UUID | None,
    room_id: UUID | None,
    venue_id: UUID | None,
    target_date: date,
    duration_minutes: int,
) -> AvailabilityResponse:
    if duration_minutes < 15:
        raise AvailabilityValidationError("durationMinutes must be at least 15.")

    context = await _resolve_resource(
        session,
        level=level,
        seat_id=seat_id,
        room_id=room_id,
        venue_id=venue_id,
    )
    booking_rule = await _resolve_booking_rule(session, context)
    if booking_rule is not None:
        if duration_minutes < booking_rule.min_duration_minutes:
            raise AvailabilityValidationError("durationMinutes is below the minimum allowed duration.")
        if duration_minutes > booking_rule.max_duration_minutes:
            raise AvailabilityValidationError("durationMinutes exceeds the maximum allowed duration.")

    operating_hours = await _resolve_operating_hours(session, context, target_date)
    if operating_hours is None:
        return AvailabilityResponse(date=target_date, timeSlots=[])

    tz = ZoneInfo(context.timezone)
    open_time, close_time = operating_hours
    local_start = datetime.combine(target_date, open_time, tzinfo=tz)
    local_close = datetime.combine(target_date, close_time, tzinfo=tz)
    duration = timedelta(minutes=duration_minutes)
    slot_end_limit = local_close

    if local_start + duration > slot_end_limit:
        return AvailabilityResponse(date=target_date, timeSlots=[])

    utc_range_start = local_start.astimezone(timezone.utc)
    utc_range_end = slot_end_limit.astimezone(timezone.utc)
    bookings, holds = await _load_conflicts(session, context, utc_range_start, utc_range_end)

    slots: list[AvailabilitySlot] = []
    current_local = local_start
    while current_local + duration <= slot_end_limit:
        slot_start_utc = current_local.astimezone(timezone.utc)
        slot_end_utc = (current_local + duration).astimezone(timezone.utc)
        is_blocked = any(_overlaps(slot_start_utc, slot_end_utc, item.start_time, item.end_time) for item in bookings)
        if not is_blocked:
            is_blocked = any(_overlaps(slot_start_utc, slot_end_utc, item.start_time, item.end_time) for item in holds)

        slots.append(
            AvailabilitySlot(
                startTime=slot_start_utc,
                endTime=slot_end_utc,
                available=not is_blocked,
                seatId=context.seat_id if context.level == BookingLevel.SEAT else None,
            )
        )
        current_local += duration

    return AvailabilityResponse(date=target_date, timeSlots=slots)
