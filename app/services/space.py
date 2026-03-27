from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import VenueStatus
from app.db.models import BookingRule, Feature, FeatureLink, Room, RoomHour, Seat, Tariff, Venue
from app.schemas.space import (
    BookingRulePublic,
    FeaturePublic,
    GeoPoint,
    RoomBrief,
    RoomFull,
    RoomHourPublic,
    RoomLayoutUpdate,
    SeatBrief,
    TariffPublic,
    VenueCreate,
    VenueFull,
    VenueListItem,
)


class SpaceNotFoundError(Exception):
    pass


def _feature_code(raw_value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", raw_value.strip().lower()).strip("_")
    return normalized or "feature"


async def _get_feature_map(
    session: AsyncSession,
    *,
    venue_ids: list[UUID] | None = None,
    room_ids: list[UUID] | None = None,
) -> dict[str, list[str]]:
    stmt = select(FeatureLink.venue_id, FeatureLink.room_id, Feature.name).join(
        Feature, Feature.id == FeatureLink.feature_id
    )

    if venue_ids is not None:
        stmt = stmt.where(FeatureLink.venue_id.in_(venue_ids))
    if room_ids is not None:
        stmt = stmt.where(FeatureLink.room_id.in_(room_ids))

    rows = (await session.execute(stmt)).all()
    feature_map: dict[str, list[str]] = {}
    for venue_id, room_id, feature_name in rows:
        key = str(room_id or venue_id)
        feature_map.setdefault(key, []).append(feature_name)
    return feature_map


async def list_venues(
    session: AsyncSession,
    *,
    q: str | None,
    location: str | None,
    capacity: int | None,
    features: list[str] | None,
) -> list[VenueListItem]:
    stmt = select(Venue)
    if q:
        q_like = f"%{q.strip()}%"
        stmt = stmt.where((Venue.name.ilike(q_like)) | (Venue.address.ilike(q_like)))
    if location:
        location_like = f"%{location.strip()}%"
        stmt = stmt.where(Venue.address.ilike(location_like))

    venues = (await session.scalars(stmt.order_by(Venue.name))).all()
    if not venues:
        return []

    venue_ids = [venue.id for venue in venues]
    feature_map = await _get_feature_map(session, venue_ids=venue_ids)
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

    requested_features = {_feature_code(value) for value in (features or [])}
    response: list[VenueListItem] = []
    for venue in venues:
        venue_features = feature_map.get(str(venue.id), [])
        if requested_features:
            venue_feature_codes = {_feature_code(value) for value in venue_features}
            if not requested_features.issubset(venue_feature_codes):
                continue

        workplaces = seat_counts.get(venue.id, 0)
        if capacity is not None and workplaces < capacity:
            continue

        response.append(
            VenueListItem(
                id=venue.id,
                name=venue.name,
                address=venue.address,
                features=sorted(venue_features),
                availableWorkplaces=workplaces,
            )
        )

    return response


async def get_venue(session: AsyncSession, venue_id: UUID) -> VenueFull:
    venue = await session.get(Venue, venue_id)
    if venue is None:
        raise SpaceNotFoundError("Venue not found.")

    rooms = (
        await session.scalars(select(Room).where(Room.venue_id == venue_id).order_by(Room.name))
    ).all()
    room_ids = [room.id for room in rooms]
    venue_feature_map = await _get_feature_map(session, venue_ids=[venue_id])
    room_feature_map = await _get_feature_map(session, room_ids=room_ids) if room_ids else {}

    return VenueFull(
        id=venue.id,
        name=venue.name,
        address=venue.address,
        timezone=venue.timezone,
        location=GeoPoint(),
        features=sorted(venue_feature_map.get(str(venue.id), [])),
        rooms=[
            RoomBrief(
                id=room.id,
                name=room.name,
                allowFullRoomBooking=room.allow_full_room_booking,
                features=sorted(room_feature_map.get(str(room.id), [])),
            )
            for room in rooms
        ],
    )


async def get_rooms_by_venue(session: AsyncSession, venue_id: UUID) -> list[RoomBrief]:
    venue = await session.get(Venue, venue_id)
    if venue is None:
        raise SpaceNotFoundError("Venue not found.")

    rooms = (
        await session.scalars(select(Room).where(Room.venue_id == venue_id).order_by(Room.name))
    ).all()
    room_feature_map = await _get_feature_map(session, room_ids=[room.id for room in rooms]) if rooms else {}
    return [
        RoomBrief(
            id=room.id,
            name=room.name,
            allowFullRoomBooking=room.allow_full_room_booking,
            features=sorted(room_feature_map.get(str(room.id), [])),
        )
        for room in rooms
    ]


async def get_seats_by_room(session: AsyncSession, room_id: UUID) -> list[SeatBrief]:
    room = await session.get(Room, room_id)
    if room is None:
        raise SpaceNotFoundError("Room not found.")

    seats = (
        await session.scalars(select(Seat).where(Seat.room_id == room_id).order_by(Seat.label))
    ).all()
    return [
        SeatBrief(
            id=seat.id,
            label=seat.label,
            gridX=seat.grid_x,
            gridY=seat.grid_y,
            seatType=seat.seat_type,
            attributes=seat.attributes,
            active=seat.active,
        )
        for seat in seats
    ]


async def get_room(session: AsyncSession, room_id: UUID) -> RoomFull:
    room = await session.get(Room, room_id)
    if room is None:
        raise SpaceNotFoundError("Room not found.")

    seats = await get_seats_by_room(session, room_id)
    room_feature_map = await _get_feature_map(session, room_ids=[room.id])
    return RoomFull(
        id=room.id,
        name=room.name,
        allowFullRoomBooking=room.allow_full_room_booking,
        features=sorted(room_feature_map.get(str(room.id), [])),
        gridWidth=room.grid_width,
        gridHeight=room.grid_height,
        seats=seats,
    )


async def list_features(session: AsyncSession) -> list[FeaturePublic]:
    features = (await session.scalars(select(Feature).order_by(Feature.name))).all()
    return [
        FeaturePublic(
            id=feature.id,
            code=feature.code,
            name=feature.name,
            icon=feature.icon,
        )
        for feature in features
    ]


async def get_room_hours(session: AsyncSession, room_id: UUID) -> list[RoomHourPublic]:
    room = await session.get(Room, room_id)
    if room is None:
        raise SpaceNotFoundError("Room not found.")

    room_hours = (
        await session.scalars(select(RoomHour).where(RoomHour.room_id == room_id).order_by(RoomHour.weekday))
    ).all()
    return [
        RoomHourPublic(
            weekday=item.weekday,
            startLocalTime=item.start_local_time.isoformat() if item.start_local_time else None,
            endLocalTime=item.end_local_time.isoformat() if item.end_local_time else None,
            isClosed=item.is_closed,
        )
        for item in room_hours
    ]


async def list_tariffs(
    session: AsyncSession,
    *,
    venue_id: UUID | None,
    room_id: UUID | None,
    seat_id: UUID | None,
) -> list[TariffPublic]:
    stmt = select(Tariff)
    if venue_id is not None:
        stmt = stmt.where(Tariff.venue_id == venue_id)
    if room_id is not None:
        stmt = stmt.where(Tariff.room_id == room_id)
    if seat_id is not None:
        stmt = stmt.where(Tariff.seat_id == seat_id)

    tariffs = (await session.scalars(stmt.order_by(Tariff.active_from.desc().nullslast(), Tariff.id))).all()
    return [
        TariffPublic(
            id=tariff.id,
            venueId=tariff.venue_id,
            roomId=tariff.room_id,
            seatId=tariff.seat_id,
            billingUnit=tariff.billing_unit,
            priceAmountCents=tariff.price_amount_cents,
            currency=tariff.currency,
            activeFrom=tariff.active_from.isoformat() if tariff.active_from else None,
            activeTo=tariff.active_to.isoformat() if tariff.active_to else None,
            archivedAt=tariff.archived_at.isoformat() if tariff.archived_at else None,
        )
        for tariff in tariffs
    ]


async def get_booking_rule(
    session: AsyncSession,
    *,
    scope: str,
    venue_id: UUID | None,
    room_id: UUID | None,
) -> BookingRulePublic:
    if scope not in {"venue", "room"}:
        raise ValueError("scope must be either 'venue' or 'room'.")
    if scope == "venue" and venue_id is None:
        raise ValueError("venueId is required for venue scope.")
    if scope == "room" and room_id is None:
        raise ValueError("roomId is required for room scope.")

    stmt = select(BookingRule)
    if scope == "venue":
        stmt = stmt.where(BookingRule.venue_id == venue_id, BookingRule.room_id.is_(None))
    else:
        stmt = stmt.where(BookingRule.room_id == room_id)

    rule = await session.scalar(stmt.order_by(BookingRule.created_at.desc()))
    if rule is None:
        raise SpaceNotFoundError("Booking rule not found.")
    return BookingRulePublic(
        id=rule.id,
        venueId=rule.venue_id,
        roomId=rule.room_id,
        minDurationMinutes=rule.min_duration_minutes,
        maxDurationMinutes=rule.max_duration_minutes,
        maxAdvanceDays=rule.max_advance_days,
        cancellationDeadlineMinutes=rule.cancellation_deadline_minutes,
        requiresPayment=rule.requires_payment,
        holdTtlSeconds=rule.hold_ttl_seconds,
        checkinOpenBeforeMinutes=rule.checkin_open_before_minutes,
        geoRadiusMeters=rule.geo_radius_meters,
    )


async def create_venue(session: AsyncSession, payload: VenueCreate) -> VenueFull:
    venue = Venue(
        name=payload.name,
        address=payload.address,
        timezone=payload.timezone,
        status=VenueStatus.ACTIVE,
    )
    session.add(venue)
    await session.flush()

    for feature_name in payload.features:
        code = _feature_code(feature_name)
        feature = await session.scalar(select(Feature).where(Feature.code == code))
        if feature is None:
            feature = Feature(code=code, name=feature_name, icon=None)
            session.add(feature)
            await session.flush()
        session.add(FeatureLink(feature_id=feature.id, venue_id=venue.id))

    await session.commit()
    return await get_venue(session, venue.id)


async def update_room_layout(session: AsyncSession, room_id: UUID, payload: RoomLayoutUpdate) -> RoomFull:
    room = await session.get(Room, room_id)
    if room is None:
        raise SpaceNotFoundError("Room not found.")

    if payload.allowFullRoomBooking is not None:
        room.allow_full_room_booking = payload.allowFullRoomBooking

    existing_seats = {
        seat.id: seat
        for seat in (
            await session.scalars(select(Seat).where(Seat.room_id == room_id))
        ).all()
    }

    for seat_payload in payload.seats:
        if seat_payload.id is not None and seat_payload.id in existing_seats:
            seat = existing_seats[seat_payload.id]
            seat.label = seat_payload.label
            seat.grid_x = seat_payload.gridX
            seat.grid_y = seat_payload.gridY
            seat.seat_type = seat_payload.seatType
            seat.attributes = seat_payload.attributes
            seat.active = seat_payload.active
            continue

        session.add(
            Seat(
                room_id=room_id,
                label=seat_payload.label,
                grid_x=seat_payload.gridX,
                grid_y=seat_payload.gridY,
                seat_type=seat_payload.seatType,
                attributes=seat_payload.attributes,
                active=seat_payload.active,
            )
        )

    await session.commit()
    await session.refresh(room)

    seats = await get_seats_by_room(session, room_id)
    room_feature_map = await _get_feature_map(session, room_ids=[room.id])
    return RoomFull(
        id=room.id,
        name=room.name,
        allowFullRoomBooking=room.allow_full_room_booking,
        features=sorted(room_feature_map.get(str(room.id), [])),
        gridWidth=room.grid_width,
        gridHeight=room.grid_height,
        seats=seats,
    )
