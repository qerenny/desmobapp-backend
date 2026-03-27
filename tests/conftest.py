from __future__ import annotations

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Booking,
    BookingRule,
    Checkin,
    FavoriteVenue,
    FeatureLink,
    Hold,
    NotificationPreference,
    QRCode,
    RefreshToken,
    Room,
    RoomHour,
    Seat,
    Transaction,
    User,
    UserRoleAssignment,
    Venue,
)
from app.db.session import SessionLocal
from app.main import app
from app.services.rbac import seed_roles_and_permissions

TEST_EMAIL_PREFIX = "pytest-"
TEST_VENUE_PREFIX = "Pytest "


async def _cleanup_test_data(session: AsyncSession) -> None:
    venue_ids = list(
        (await session.scalars(select(Venue.id).where(Venue.name.like(f"{TEST_VENUE_PREFIX}%")))).all()
    )
    room_ids = list((await session.scalars(select(Room.id).where(Room.venue_id.in_(venue_ids)))).all()) if venue_ids else []
    seat_ids = list((await session.scalars(select(Seat.id).where(Seat.room_id.in_(room_ids)))).all()) if room_ids else []
    user_ids = list(
        (await session.scalars(select(User.id).where(User.email.like(f"{TEST_EMAIL_PREFIX}%@example.com")))).all()
    )
    booking_ids = list((await session.scalars(select(Booking.id).where(Booking.user_id.in_(user_ids)))).all()) if user_ids else []

    if booking_ids:
        await session.execute(delete(Checkin).where(Checkin.booking_id.in_(booking_ids)))
        await session.execute(delete(QRCode).where(QRCode.booking_id.in_(booking_ids)))
        await session.execute(delete(Transaction).where(Transaction.booking_id.in_(booking_ids)))
        await session.execute(delete(Booking).where(Booking.id.in_(booking_ids)))

    if seat_ids:
        await session.execute(delete(Hold).where(Hold.seat_id.in_(seat_ids)))
        await session.execute(delete(FeatureLink).where(FeatureLink.seat_id.in_(seat_ids)))
        await session.execute(delete(Seat).where(Seat.id.in_(seat_ids)))

    if room_ids:
        await session.execute(delete(RoomHour).where(RoomHour.room_id.in_(room_ids)))
        await session.execute(delete(BookingRule).where(BookingRule.room_id.in_(room_ids)))
        await session.execute(delete(FeatureLink).where(FeatureLink.room_id.in_(room_ids)))
        await session.execute(delete(Room).where(Room.id.in_(room_ids)))

    if venue_ids:
        await session.execute(delete(FavoriteVenue).where(FavoriteVenue.venue_id.in_(venue_ids)))
        await session.execute(delete(BookingRule).where(BookingRule.venue_id.in_(venue_ids)))
        await session.execute(delete(FeatureLink).where(FeatureLink.venue_id.in_(venue_ids)))
        await session.execute(delete(Venue).where(Venue.id.in_(venue_ids)))

    if user_ids:
        await session.execute(delete(FavoriteVenue).where(FavoriteVenue.user_id.in_(user_ids)))
        await session.execute(delete(NotificationPreference).where(NotificationPreference.user_id.in_(user_ids)))
        await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(user_ids)))
        await session.execute(delete(UserRoleAssignment).where(UserRoleAssignment.user_id.in_(user_ids)))
        await session.execute(delete(User).where(User.id.in_(user_ids)))

    await session.commit()


@pytest_asyncio.fixture(autouse=True)
async def prepare_test_environment() -> AsyncIterator[None]:
    async with SessionLocal() as session:
        await seed_roles_and_permissions(session)
        await _cleanup_test_data(session)
    yield
    async with SessionLocal() as session:
        await _cleanup_test_data(session)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
