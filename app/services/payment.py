from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, PaymentStatus
from app.db.models import Booking, Transaction, User
from app.schemas.payment import PaymentCreateRequest, TransactionResponse


class PaymentValidationError(Exception):
    pass


class PaymentNotFoundError(Exception):
    pass


def _serialize_transaction(transaction: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=transaction.id,
        bookingId=transaction.booking_id,
        userId=transaction.user_id,
        provider=transaction.provider,
        externalId=transaction.external_id,
        status=transaction.status,
        amountCents=transaction.amount_cents,
        refundedCents=transaction.refunded_cents,
        currency=transaction.currency,
        metadata=transaction.metadata_,
        authorizedAt=transaction.authorized_at,
        capturedAt=transaction.captured_at,
        refundedAt=transaction.refunded_at,
        createdAt=transaction.created_at,
        updatedAt=transaction.updated_at,
    )


async def create_payment(
    session: AsyncSession,
    *,
    current_user: User,
    payload: PaymentCreateRequest,
) -> TransactionResponse:
    booking = await session.scalar(
        select(Booking).where(Booking.id == payload.bookingId, Booking.user_id == current_user.id)
    )
    if booking is None:
        raise PaymentNotFoundError("Booking not found.")
    if booking.status == BookingStatus.CANCELLED:
        raise PaymentValidationError("Cancelled booking cannot be paid.")

    now = datetime.now(timezone.utc)
    provider = payload.provider or "mock"
    transaction = Transaction(
        booking_id=booking.id,
        user_id=current_user.id,
        provider=provider,
        external_id=f"mock_{uuid4().hex}",
        status=PaymentStatus.CAPTURED,
        amount_cents=payload.amountCents,
        refunded_cents=0,
        currency=payload.currency.upper(),
        metadata_={"mode": "mock", "provider": provider},
        authorized_at=now,
        captured_at=now,
    )
    session.add(transaction)

    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED

    await session.commit()
    await session.refresh(transaction)
    return _serialize_transaction(transaction)
