from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel


class AvailabilitySlot(BaseModel):
    startTime: datetime
    endTime: datetime
    available: bool
    seatId: UUID | None = None


class AvailabilityResponse(BaseModel):
    date: date
    timeSlots: list[AvailabilitySlot]
