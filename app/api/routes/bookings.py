from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.enums import BookingStatus
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.booking import BookingCreateRequest, BookingListResponse, BookingResponse
from app.schemas.checkin import CheckinRequest, CheckinResponse
from app.services.availability import AvailabilityNotFoundError, AvailabilityValidationError
from app.services.booking import (
    BookingConflictError,
    BookingNotFoundError,
    cancel_booking,
    create_booking,
    get_booking,
    list_bookings,
)
from app.services.checkin import CheckinNotFoundError, CheckinValidationError, create_checkin

router = APIRouter(tags=["Bookings"])


@router.post("/bookings", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
async def create_booking_endpoint(
    payload: BookingCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    try:
        return await create_booking(session, current_user=current_user, payload=payload)
    except AvailabilityValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except AvailabilityNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except BookingConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/bookings/{bookingId}", response_model=BookingResponse)
async def get_booking_endpoint(
    bookingId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BookingResponse:
    try:
        return await get_booking(session, booking_id=bookingId, current_user=current_user)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/me/bookings", response_model=BookingListResponse, summary="List current user bookings")
@router.get("/bookings", response_model=BookingListResponse, include_in_schema=False)
async def list_bookings_endpoint(
    status_filter: BookingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None, alias="dateFrom"),
    date_to: date | None = Query(default=None, alias="dateTo"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> BookingListResponse:
    return await list_bookings(
        session,
        current_user=current_user,
        status=status_filter,
        date_from=date_from,
        date_to=date_to,
        page=page,
        limit=limit,
    )


@router.delete("/bookings/{bookingId}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking_endpoint(
    bookingId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    try:
        await cancel_booking(session, booking_id=bookingId, current_user=current_user)
    except BookingNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bookings/{bookingId}/checkin", response_model=CheckinResponse)
async def booking_checkin_endpoint(
    bookingId: UUID,
    payload: CheckinRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> CheckinResponse:
    try:
        return await create_checkin(session, booking_id=bookingId, current_user=current_user, payload=payload)
    except CheckinValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except CheckinNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
