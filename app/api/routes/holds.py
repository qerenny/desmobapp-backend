from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.hold import HoldCreateRequest, HoldResponse
from app.services.availability import AvailabilityNotFoundError, AvailabilityValidationError
from app.services.hold import HoldConflictError, HoldNotFoundError, cancel_hold, create_hold

router = APIRouter(tags=["Holds"])


@router.post("/holds", response_model=HoldResponse, status_code=status.HTTP_201_CREATED)
async def create_hold_endpoint(
    payload: HoldCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> HoldResponse:
    try:
        return await create_hold(
            session,
            current_user=current_user,
            payload=payload,
        )
    except AvailabilityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AvailabilityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except HoldConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.delete("/holds/{holdId}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_hold_endpoint(
    holdId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        await cancel_hold(session, hold_id=holdId, current_user=current_user)
    except HoldNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return Response(status_code=status.HTTP_204_NO_CONTENT)
