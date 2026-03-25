from __future__ import annotations

import uuid
from datetime import date, time

from geoalchemy2 import Geometry
from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.enums import VenueStatus
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class Venue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "venues"
    __table_args__ = (Index("ix_venues_location_gist", "location", postgresql_using="gist"),)

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Europe/Moscow")
    location: Mapped[str | None] = mapped_column(Geometry("POINT", srid=4326, spatial_index=False))
    status: Mapped[VenueStatus] = mapped_column(
        Enum(VenueStatus, name="venue_status"),
        default=VenueStatus.DRAFT,
        nullable=False,
    )


class Room(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "rooms"

    venue_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("venues.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    allow_full_room_booking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    grid_width: Mapped[int | None] = mapped_column(Integer)
    grid_height: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Seat(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "seats"
    __table_args__ = (UniqueConstraint("room_id", "label", name="uq_seats_room_label"),)

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    grid_x: Mapped[int] = mapped_column(Integer, nullable=False)
    grid_y: Mapped[int] = mapped_column(Integer, nullable=False)
    seat_type: Mapped[str | None] = mapped_column(String(64))
    attributes: Mapped[dict | None] = mapped_column(JSONB)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Feature(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "features"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(128))


class FeatureLink(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "feature_links"

    feature_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("features.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    seat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("seats.id"))


class RoomHour(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "room_hours"
    __table_args__ = (UniqueConstraint("room_id", "weekday", name="uq_room_hours_room_weekday"),)

    room_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rooms.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_local_time: Mapped[time | None] = mapped_column(Time)
    end_local_time: Mapped[time | None] = mapped_column(Time)
    is_closed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Tariff(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "tariffs"

    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    seat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("seats.id"))
    billing_unit: Mapped[str] = mapped_column(String(32), nullable=False, default="hour")
    price_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="RUB")
    active_from: Mapped[date | None] = mapped_column(Date)
    active_to: Mapped[date | None] = mapped_column(Date)
    archived_at: Mapped[date | None] = mapped_column(Date)


class BookingRule(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "booking_rules"

    venue_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("venues.id"))
    room_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rooms.id"))
    min_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    max_duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=480)
    max_advance_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    cancellation_deadline_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    requires_payment: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hold_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    checkin_open_before_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    geo_radius_meters: Mapped[int] = mapped_column(Integer, nullable=False, default=150)
