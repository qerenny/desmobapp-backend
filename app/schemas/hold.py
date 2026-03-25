from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.enums import BookingLevel


class HoldCreateRequest(BaseModel):
    level: BookingLevel
    seatId: UUID | None = None
    roomId: UUID | None = None
    venueId: UUID | None = None
    startTime: datetime
    endTime: datetime


class HoldResponse(BaseModel):
    id: UUID
    level: BookingLevel
    seatId: UUID | None = None
    roomId: UUID | None = None
    venueId: UUID
    userId: UUID
    startTime: datetime
    endTime: datetime
    expiresAt: datetime
    status: str
    createdAt: datetime
