from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.db.enums import CheckinMethod


class CheckinRequest(BaseModel):
    method: CheckinMethod
    lat: float | None = None
    lon: float | None = None
    qrCode: str | None = None


class CheckinLocation(BaseModel):
    lat: float | None = None
    lon: float | None = None


class CheckinResponse(BaseModel):
    id: UUID
    bookingId: UUID
    method: CheckinMethod
    location: CheckinLocation
    checkedInAt: datetime
    notes: str | None = None
