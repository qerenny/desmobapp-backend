from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.common import MessageResponse
from app.schemas.payment import PaymentCreateRequest, PaymentRefundRequest, TransactionResponse
from app.services.payment import (
    PaymentNotFoundError,
    PaymentValidationError,
    capture_payment,
    create_payment,
    get_payment,
    refund_payment,
)

router = APIRouter(tags=["Payments"])


@router.post("/payments", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_payment_endpoint(
    payload: PaymentCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    try:
        return await create_payment(session, current_user=current_user, payload=payload)
    except PaymentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/payments/{paymentId}", response_model=TransactionResponse)
async def get_payment_endpoint(
    paymentId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    try:
        return await get_payment(session, payment_id=paymentId, current_user=current_user)
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/payments/{paymentId}/capture", response_model=TransactionResponse)
async def capture_payment_endpoint(
    paymentId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    try:
        return await capture_payment(session, payment_id=paymentId, current_user=current_user)
    except PaymentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/payments/{paymentId}/refund", response_model=TransactionResponse)
async def refund_payment_endpoint(
    paymentId: UUID,
    payload: PaymentRefundRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> TransactionResponse:
    try:
        return await refund_payment(session, payment_id=paymentId, current_user=current_user, payload=payload)
    except PaymentValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except PaymentNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/payments/webhooks/{provider}", response_model=MessageResponse)
async def mock_payment_webhook(
    provider: str,
    payload: dict[str, Any] = Body(default_factory=dict),
) -> MessageResponse:
    event = payload.get("event", "accepted")
    return MessageResponse(message=f"Mock webhook accepted for provider={provider}, event={event}.")
