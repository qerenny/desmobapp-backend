from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.db.enums import PaymentStatus


class PaymentCreateRequest(BaseModel):
    bookingId: UUID
    amountCents: int = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    provider: str | None = None


class TransactionResponse(BaseModel):
    id: UUID
    bookingId: UUID
    userId: UUID
    provider: str
    externalId: str | None = None
    status: PaymentStatus
    amountCents: int
    refundedCents: int
    currency: str
    metadata: dict | None = None
    authorizedAt: datetime | None = None
    capturedAt: datetime | None = None
    refundedAt: datetime | None = None
    createdAt: datetime
    updatedAt: datetime


class PaymentRefundRequest(BaseModel):
    amountCents: int | None = Field(default=None, ge=1)
