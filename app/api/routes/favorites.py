from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import get_current_user
from app.db.models import User
from app.db.session import get_db_session
from app.schemas.favorite import FavoriteCreateRequest
from app.schemas.space import VenueListItem
from app.services.favorite import (
    FavoriteNotFoundError,
    create_favorite_venue,
    delete_favorite_venue,
    list_favorite_venues,
)

router = APIRouter(tags=["Favorites"])


@router.get("/favorites", response_model=list[VenueListItem], summary="List favorite venues")
async def get_favorites(
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> list[VenueListItem]:
    return await list_favorite_venues(session, current_user=current_user)


@router.post("/favorites", response_model=VenueListItem, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    payload: FavoriteCreateRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> VenueListItem:
    try:
        return await create_favorite_venue(session, current_user=current_user, payload=payload)
    except FavoriteNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.delete("/favorites/{venueId}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    venueId: UUID,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> Response:
    await delete_favorite_venue(session, current_user=current_user, venue_id=venueId)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
