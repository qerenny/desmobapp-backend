from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.enums import BookingLevel
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.availability import AvailabilityResponse
from app.services.availability import (
    AvailabilityNotFoundError,
    AvailabilityValidationError,
    get_availability,
)

router = APIRouter(tags=["Availability"])


@router.get("/availability", response_model=AvailabilityResponse, summary="Get resource availability")
async def availability(
    level: BookingLevel,
    date_: date = Query(alias="date"),
    duration_minutes: int = Query(default=60, alias="durationMinutes", ge=15),
    seatId: UUID | None = None,
    roomId: UUID | None = None,
    venueId: UUID | None = None,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> AvailabilityResponse:
    try:
        return await get_availability(
            session,
            level=level,
            seat_id=seatId,
            room_id=roomId,
            venue_id=venueId,
            target_date=date_,
            duration_minutes=duration_minutes,
        )
    except AvailabilityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AvailabilityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
