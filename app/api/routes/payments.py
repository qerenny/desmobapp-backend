from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.payment import PaymentCreateRequest, TransactionResponse
from app.services.payment import PaymentNotFoundError, PaymentValidationError, create_payment

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
