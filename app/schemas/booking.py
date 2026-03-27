from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.enums import BookingLevel, BookingStatus


class BookingCreateRequest(BaseModel):
    level: BookingLevel
    seatId: UUID | None = None
    roomId: UUID | None = None
    venueId: UUID | None = None
    holdId: UUID | None = None
    startTime: datetime
    endTime: datetime


class BookingResponse(BaseModel):
    id: UUID
    level: BookingLevel
    status: BookingStatus
    seatId: UUID | None = None
    roomId: UUID | None = None
    venueId: UUID
    userId: UUID
    holdId: UUID | None = None
    startTime: datetime
    endTime: datetime
    priceAmountCents: int
    priceCurrency: str
    createdAt: datetime
    updatedAt: datetime
    cancelledAt: datetime | None = None


class BookingListItem(BaseModel):
    id: UUID
    status: BookingStatus
    level: BookingLevel
    seatId: UUID | None = None
    roomId: UUID | None = None
    venueId: UUID
    startTime: datetime
    endTime: datetime
    priceAmountCents: int
    priceCurrency: str
    createdAt: datetime
    cancelledAt: datetime | None = None


class BookingListResponse(BaseModel):
    items: list[BookingListItem]
    page: int
    limit: int
    total: int


class BookingWindowUpdateRequest(BaseModel):
    startTime: datetime
    endTime: datetime
