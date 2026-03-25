from __future__ import annotations

from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user, require_permissions
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.space import RoomBrief, RoomFull, RoomLayoutUpdate, SeatBrief, VenueCreate, VenueFull, VenueListItem
from app.services.space import (
    SpaceNotFoundError,
    create_venue,
    get_rooms_by_venue,
    get_seats_by_room,
    get_venue,
    list_venues,
    update_room_layout,
)

router = APIRouter(tags=["Venues"])
admin_router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get("/venues", response_model=list[VenueListItem], summary="Search venues")
async def venues(
    q: str | None = None,
    location: str | None = None,
    date_: date | None = Query(default=None, alias="date"),
    capacity: int | None = Query(default=None, ge=1),
    features: list[str] | None = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[VenueListItem]:
    return await list_venues(
        session,
        q=q,
        location=location,
        capacity=capacity,
        features=features,
    )


@router.get("/venues/{venueId}", response_model=VenueFull, summary="Get venue details")
async def venue_details(
    venueId: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> VenueFull:
    try:
        return await get_venue(session, venueId)
    except SpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/venues/{venueId}/rooms", response_model=list[RoomBrief], summary="Get venue rooms")
async def venue_rooms(
    venueId: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[RoomBrief]:
    try:
        return await get_rooms_by_venue(session, venueId)
    except SpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/rooms/{roomId}/seats", response_model=list[SeatBrief], summary="Get room seats")
async def room_seats(
    roomId: UUID,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
) -> list[SeatBrief]:
    try:
        return await get_seats_by_room(session, roomId)
    except SpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@admin_router.post("/venues", response_model=VenueFull, status_code=status.HTTP_201_CREATED)
async def admin_create_venue(
    payload: VenueCreate,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
    __=Depends(require_permissions("venues.update")),
) -> VenueFull:
    return await create_venue(session, payload)


@admin_router.put("/rooms/{roomId}/layout", response_model=RoomFull)
async def admin_update_room_layout(
    roomId: UUID,
    payload: RoomLayoutUpdate,
    session: AsyncSession = Depends(get_db_session),
    _: User = Depends(get_current_user),
    __=Depends(require_permissions("rooms.update")),
) -> RoomFull:
    try:
        return await update_room_layout(session, roomId, payload)
    except SpaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
