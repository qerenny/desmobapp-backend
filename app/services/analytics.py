from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus
from app.db.models import Booking, Room, Seat
from app.schemas.analytics import AnalyticsPeriod, OccupancyAnalyticsResponse


async def get_occupancy_analytics(
    session: AsyncSession,
    *,
    start_date: date,
    end_date: date,
) -> OccupancyAnalyticsResponse:
    period_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    period_end = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)

    bookings = (
        await session.scalars(
            select(Booking).where(
                Booking.status.in_(
                    {
                        BookingStatus.PENDING,
                        BookingStatus.CONFIRMED,
                        BookingStatus.CHECKED_IN,
                        BookingStatus.COMPLETED,
                    }
                ),
                Booking.start_time < period_end,
                Booking.end_time > period_start,
            )
        )
    ).all()

    total_bookings = len(bookings)
    total_revenue_cents = sum(booking.price_amount_cents for booking in bookings)
    total_booked_minutes = 0
    for booking in bookings:
        effective_start = max(booking.start_time, period_start)
        effective_end = min(booking.end_time, period_end)
        total_booked_minutes += max(0, int((effective_end - effective_start).total_seconds() // 60))

    active_seats = await session.scalar(select(func.count()).select_from(Seat).where(Seat.active.is_(True)))
    if active_seats is None or active_seats == 0:
        active_rooms = await session.scalar(select(func.count()).select_from(Room))
        capacity_units = active_rooms or 1
    else:
        capacity_units = active_seats

    total_period_minutes = max(1, capacity_units * int((period_end - period_start).total_seconds() // 60))
    occupancy_rate = min(1.0, total_booked_minutes / total_period_minutes)

    return OccupancyAnalyticsResponse(
        period=AnalyticsPeriod(startDate=start_date, endDate=end_date),
        occupancyRate=round(occupancy_rate, 4),
        totalBookings=total_bookings,
        revenue=round(total_revenue_cents / 100, 2),
    )
