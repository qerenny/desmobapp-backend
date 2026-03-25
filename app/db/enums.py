from __future__ import annotations

from enum import StrEnum


class UserStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"


class BookingLevel(StrEnum):
    SEAT = "seat"
    ROOM = "room"
    VENUE = "venue"


class BookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    NO_SHOW = "no_show"
    COMPLETED = "completed"


class HoldStatus(StrEnum):
    PENDING = "pending"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    CONVERTED = "converted"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    AUTHORIZED = "authorized"
    CAPTURED = "captured"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


class NotificationChannel(StrEnum):
    PUSH = "push"
    EMAIL = "email"


class NotificationStatus(StrEnum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InviteStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CheckinMethod(StrEnum):
    QR = "qr"
    MANUAL = "manual"
    GEO = "geo"


class VenueStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"
