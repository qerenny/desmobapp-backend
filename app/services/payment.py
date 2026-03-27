from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, PaymentStatus
from app.db.models import Booking, Transaction, User
from app.schemas.payment import PaymentCreateRequest, PaymentRefundRequest, TransactionResponse
from app.services.notification import create_notification_record


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

    now = datetime.now(UTC)
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
    await session.flush()

    if booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED

    await create_notification_record(
        session,
        user_id=current_user.id,
        template_code="payment_captured",
        payload={"bookingId": str(booking.id), "transactionId": str(transaction.id)},
    )
    await session.commit()
    await session.refresh(transaction)
    return _serialize_transaction(transaction)


async def get_payment(
    session: AsyncSession,
    *,
    payment_id: UUID,
    current_user: User,
) -> TransactionResponse:
    transaction = await session.scalar(
        select(Transaction).where(Transaction.id == payment_id, Transaction.user_id == current_user.id)
    )
    if transaction is None:
        raise PaymentNotFoundError("Payment not found.")
    return _serialize_transaction(transaction)


async def capture_payment(
    session: AsyncSession,
    *,
    payment_id: UUID,
    current_user: User,
) -> TransactionResponse:
    transaction = await session.scalar(
        select(Transaction).where(Transaction.id == payment_id, Transaction.user_id == current_user.id)
    )
    if transaction is None:
        raise PaymentNotFoundError("Payment not found.")
    if transaction.status in {PaymentStatus.CAPTURED, PaymentStatus.REFUNDED}:
        return _serialize_transaction(transaction)
    if transaction.status not in {PaymentStatus.PENDING, PaymentStatus.AUTHORIZED}:
        raise PaymentValidationError("Payment cannot be captured.")

    now = datetime.now(UTC)
    transaction.status = PaymentStatus.CAPTURED
    transaction.authorized_at = transaction.authorized_at or now
    transaction.captured_at = now
    booking = await session.get(Booking, transaction.booking_id)
    if booking is not None and booking.status == BookingStatus.PENDING:
        booking.status = BookingStatus.CONFIRMED
    await create_notification_record(
        session,
        user_id=current_user.id,
        template_code="payment_captured",
        payload={"transactionId": str(transaction.id)},
    )
    await session.commit()
    await session.refresh(transaction)
    return _serialize_transaction(transaction)


async def refund_payment(
    session: AsyncSession,
    *,
    payment_id: UUID,
    current_user: User,
    payload: PaymentRefundRequest,
) -> TransactionResponse:
    transaction = await session.scalar(
        select(Transaction).where(Transaction.id == payment_id, Transaction.user_id == current_user.id)
    )
    if transaction is None:
        raise PaymentNotFoundError("Payment not found.")
    if transaction.status not in {PaymentStatus.CAPTURED, PaymentStatus.REFUNDED}:
        raise PaymentValidationError("Only captured payments can be refunded.")

    remaining = transaction.amount_cents - transaction.refunded_cents
    refund_amount = payload.amountCents or remaining
    if refund_amount <= 0 or refund_amount > remaining:
        raise PaymentValidationError("Invalid refund amount.")

    transaction.refunded_cents += refund_amount
    if transaction.refunded_cents == transaction.amount_cents:
        transaction.status = PaymentStatus.REFUNDED
    transaction.refunded_at = datetime.now(UTC)
    await create_notification_record(
        session,
        user_id=current_user.id,
        template_code="payment_refunded",
        payload={"transactionId": str(transaction.id), "amountCents": refund_amount},
    )
    await session.commit()
    await session.refresh(transaction)
    return _serialize_transaction(transaction)
