from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import BookingLevel, BookingStatus, CheckinMethod, HoldStatus
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Hold(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "holds"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level: Mapped[BookingLevel] = mapped_column(
        Enum(BookingLevel, name="booking_level"),
        nullable=False,
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    seat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("seats.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[HoldStatus] = mapped_column(
        Enum(HoldStatus, name="hold_status"),
        default=HoldStatus.PENDING,
        nullable=False,
        index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Booking(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "bookings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    hold_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("holds.id"))
    level: Mapped[BookingLevel] = mapped_column(
        Enum(BookingLevel, name="booking_level", create_type=False),
        nullable=False,
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    seat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("seats.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status"),
        default=BookingStatus.PENDING,
        nullable=False,
        index=True,
    )
    price_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    price_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BookingEvent(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "booking_events"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Checkin(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "checkins"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    method: Mapped[CheckinMethod] = mapped_column(
        Enum(CheckinMethod, name="checkin_method"),
        nullable=False,
    )
    lat: Mapped[float | None] = mapped_column(Float)
    lon: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str | None] = mapped_column(Text)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class QRCode(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "qr_codes"

    booking_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    code: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_used: Mapped[bool] = mapped_column(nullable=False, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
