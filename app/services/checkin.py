from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, CheckinMethod
from app.db.models import Booking, Checkin, User
from app.schemas.checkin import CheckinLocation, CheckinRequest, CheckinResponse


class CheckinValidationError(Exception):
    pass


class CheckinNotFoundError(Exception):
    pass


def _serialize_checkin(checkin: Checkin) -> CheckinResponse:
    return CheckinResponse(
        id=checkin.id,
        bookingId=checkin.booking_id,
        method=checkin.method,
        location=CheckinLocation(lat=checkin.lat, lon=checkin.lon),
        checkedInAt=checkin.checked_in_at,
        notes=checkin.notes,
    )


async def create_checkin(
    session: AsyncSession,
    *,
    booking_id: UUID,
    current_user: User,
    payload: CheckinRequest,
) -> CheckinResponse:
    booking = await session.scalar(select(Booking).where(Booking.id == booking_id, Booking.user_id == current_user.id))
    if booking is None:
        raise CheckinNotFoundError("Booking not found.")
    if booking.status == BookingStatus.CANCELLED:
        raise CheckinValidationError("Cancelled booking cannot be checked in.")
    if booking.status == BookingStatus.CHECKED_IN:
        raise CheckinValidationError("Booking is already checked in.")

    if payload.method == CheckinMethod.GEO and (payload.lat is None or payload.lon is None):
        raise CheckinValidationError("Geo check-in requires lat and lon.")
    if payload.method == CheckinMethod.QR and not payload.qrCode:
        raise CheckinValidationError("QR check-in requires qrCode.")

    checkin = Checkin(
        booking_id=booking.id,
        method=payload.method,
        lat=payload.lat,
        lon=payload.lon,
        notes=payload.qrCode if payload.method == CheckinMethod.QR else None,
        checked_in_at=datetime.now(UTC),
    )
    booking.status = BookingStatus.CHECKED_IN
    session.add(checkin)
    await session.commit()
    await session.refresh(checkin)
    return _serialize_checkin(checkin)
