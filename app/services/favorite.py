from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import FavoriteVenue, Feature, FeatureLink, Room, Seat, User, Venue
from app.schemas.favorite import FavoriteCreateRequest
from app.schemas.space import VenueListItem


class FavoriteNotFoundError(Exception):
    pass


async def _build_venue_list_items(
    session: AsyncSession,
    *,
    venues: list[Venue],
) -> list[VenueListItem]:
    if not venues:
        return []

    venue_ids = [venue.id for venue in venues]
    feature_rows = (
        await session.execute(
            select(FeatureLink.venue_id, Feature.name)
            .join(Feature, Feature.id == FeatureLink.feature_id)
            .where(FeatureLink.venue_id.in_(venue_ids))
        )
    ).all()
    feature_map: dict[str, list[str]] = {}
    for venue_id, feature_name in feature_rows:
        feature_map.setdefault(str(venue_id), []).append(feature_name)

    seat_counts = dict(
        (
            await session.execute(
                select(Room.venue_id, func.count(Seat.id))
                .join(Seat, Seat.room_id == Room.id)
                .where(Seat.active.is_(True), Room.venue_id.in_(venue_ids))
                .group_by(Room.venue_id)
            )
        ).all()
    )

    return [
        VenueListItem(
            id=venue.id,
            name=venue.name,
            address=venue.address,
            features=sorted(feature_map.get(str(venue.id), [])),
            availableWorkplaces=seat_counts.get(venue.id, 0),
        )
        for venue in venues
    ]


async def list_favorite_venues(
    session: AsyncSession,
    *,
    current_user: User,
) -> list[VenueListItem]:
    venues = (
        await session.scalars(
            select(Venue)
            .join(FavoriteVenue, FavoriteVenue.venue_id == Venue.id)
            .where(FavoriteVenue.user_id == current_user.id)
            .order_by(FavoriteVenue.created_at.desc())
        )
    ).all()
    return await _build_venue_list_items(session, venues=venues)


async def create_favorite_venue(
    session: AsyncSession,
    *,
    current_user: User,
    payload: FavoriteCreateRequest,
) -> VenueListItem:
    venue = await session.get(Venue, payload.venueId)
    if venue is None:
        raise FavoriteNotFoundError("Venue not found.")

    favorite = await session.scalar(
        select(FavoriteVenue).where(
            FavoriteVenue.user_id == current_user.id,
            FavoriteVenue.venue_id == payload.venueId,
        )
    )
    if favorite is None:
        session.add(FavoriteVenue(user_id=current_user.id, venue_id=payload.venueId))
        await session.commit()

    return (await _build_venue_list_items(session, venues=[venue]))[0]


async def delete_favorite_venue(
    session: AsyncSession,
    *,
    current_user: User,
    venue_id: UUID,
) -> None:
    favorite = await session.scalar(
        select(FavoriteVenue).where(
            FavoriteVenue.user_id == current_user.id,
            FavoriteVenue.venue_id == venue_id,
        )
    )
    if favorite is None:
        return

    await session.delete(favorite)
    await session.commit()
