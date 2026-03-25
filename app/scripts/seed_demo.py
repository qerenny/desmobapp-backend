from __future__ import annotations

import asyncio
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import time

from sqlalchemy import select

from app.core.security import hash_password
from app.db.enums import UserStatus, VenueStatus
from app.db.models import (
    BookingRule,
    Feature,
    FeatureLink,
    Role,
    Room,
    RoomHour,
    Seat,
    User,
    UserRoleAssignment,
    Venue,
)
from app.db.session import SessionLocal
from app.services.rbac import seed_roles_and_permissions

DEMO_PASSWORD = "demo12345"
DEMO_VENUE_NAME = "Demo Frontend Coworking"
DEMO_VENUE_ADDRESS = "Saint Petersburg, Kronverkskiy pr. 49"
DEMO_TIMEZONE = "Europe/Moscow"
DEMO_FEATURES = ["Wi-Fi", "Coffee", "Meeting Rooms", "Parking", "Silent Zone"]


@dataclass(frozen=True)
class DemoUserSeed:
    email: str
    name: str
    global_role: str | None = None
    venue_role: str | None = None


DEMO_USERS: tuple[DemoUserSeed, ...] = (
    DemoUserSeed("demo.client@example.com", "Demo Client", global_role="client"),
    DemoUserSeed("demo.admin@example.com", "Demo Admin", global_role="admin"),
    DemoUserSeed("demo.manager@example.com", "Demo Manager", venue_role="manager"),
    DemoUserSeed("demo.owner@example.com", "Demo Owner", venue_role="owner"),
    DemoUserSeed("demo.support@example.com", "Demo Support", global_role="support"),
    DemoUserSeed("demo.billing@example.com", "Demo Billing", global_role="billing"),
    DemoUserSeed("demo.auditor@example.com", "Demo Auditor", global_role="auditor"),
)


def _feature_code(raw_value: str) -> str:
    return "_".join(part for part in raw_value.strip().lower().replace("-", " ").split() if part)


async def _get_or_create_user(email: str, name: str) -> User:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                password_hash=hash_password(DEMO_PASSWORD),
                name=name,
                status=UserStatus.ACTIVE,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

        user.name = name
        user.password_hash = hash_password(DEMO_PASSWORD)
        user.status = UserStatus.ACTIVE
        await session.commit()
        await session.refresh(user)
        return user


async def _ensure_feature_links(session, *, venue_id, names: Iterable[str]) -> None:
    for name in names:
        code = _feature_code(name)
        feature = await session.scalar(select(Feature).where(Feature.code == code))
        if feature is None:
            feature = Feature(code=code, name=name, icon=None)
            session.add(feature)
            await session.flush()

        link = await session.scalar(
            select(FeatureLink).where(
                FeatureLink.feature_id == feature.id,
                FeatureLink.venue_id == venue_id,
                FeatureLink.room_id.is_(None),
                FeatureLink.seat_id.is_(None),
            )
        )
        if link is None:
            session.add(FeatureLink(feature_id=feature.id, venue_id=venue_id))


async def _ensure_room_hours(session, *, room_id) -> None:
    for weekday in range(7):
        room_hour = await session.scalar(
            select(RoomHour).where(RoomHour.room_id == room_id, RoomHour.weekday == weekday)
        )
        if room_hour is None:
            session.add(
                RoomHour(
                    room_id=room_id,
                    weekday=weekday,
                    start_local_time=time(hour=9, minute=0),
                    end_local_time=time(hour=21, minute=0),
                    is_closed=False,
                )
            )
            continue

        room_hour.start_local_time = time(hour=9, minute=0)
        room_hour.end_local_time = time(hour=21, minute=0)
        room_hour.is_closed = False


async def _ensure_room(
    session,
    *,
    venue_id,
    name: str,
    allow_full_room_booking: bool,
    grid_width: int,
    grid_height: int,
    seat_labels: list[str],
) -> Room:
    room = await session.scalar(select(Room).where(Room.venue_id == venue_id, Room.name == name))
    if room is None:
        room = Room(
            venue_id=venue_id,
            name=name,
            allow_full_room_booking=allow_full_room_booking,
            grid_width=grid_width,
            grid_height=grid_height,
            status="active",
        )
        session.add(room)
        await session.flush()
    else:
        room.allow_full_room_booking = allow_full_room_booking
        room.grid_width = grid_width
        room.grid_height = grid_height
        room.status = "active"

    for index, label in enumerate(seat_labels, start=1):
        grid_x = ((index - 1) % max(grid_width, 1)) + 1
        grid_y = ((index - 1) // max(grid_width, 1)) + 1
        seat = await session.scalar(select(Seat).where(Seat.room_id == room.id, Seat.label == label))
        if seat is None:
            session.add(
                Seat(
                    room_id=room.id,
                    label=label,
                    grid_x=grid_x,
                    grid_y=grid_y,
                    seat_type="desk",
                    attributes={"monitor": True},
                    active=True,
                )
            )
            continue

        seat.grid_x = grid_x
        seat.grid_y = grid_y
        seat.seat_type = "desk"
        seat.attributes = {"monitor": True}
        seat.active = True

    await _ensure_room_hours(session, room_id=room.id)
    return room


async def main() -> None:
    async with SessionLocal() as session:
        await seed_roles_and_permissions(session)

        venue = await session.scalar(select(Venue).where(Venue.name == DEMO_VENUE_NAME))
        if venue is None:
            venue = Venue(
                name=DEMO_VENUE_NAME,
                address=DEMO_VENUE_ADDRESS,
                timezone=DEMO_TIMEZONE,
                status=VenueStatus.ACTIVE,
            )
            session.add(venue)
            await session.flush()
        else:
            venue.address = DEMO_VENUE_ADDRESS
            venue.timezone = DEMO_TIMEZONE
            venue.status = VenueStatus.ACTIVE

        await _ensure_feature_links(session, venue_id=venue.id, names=DEMO_FEATURES)

        await _ensure_room(
            session,
            venue_id=venue.id,
            name="Open Space A",
            allow_full_room_booking=False,
            grid_width=4,
            grid_height=2,
            seat_labels=["A-1", "A-2", "A-3", "A-4", "A-5", "A-6"],
        )
        meeting_room = await _ensure_room(
            session,
            venue_id=venue.id,
            name="Meeting Room B",
            allow_full_room_booking=True,
            grid_width=2,
            grid_height=2,
            seat_labels=["B-1", "B-2", "B-3", "B-4"],
        )

        venue_rule = await session.scalar(
            select(BookingRule).where(BookingRule.venue_id == venue.id, BookingRule.room_id.is_(None))
        )
        if venue_rule is None:
            venue_rule = BookingRule(
                venue_id=venue.id,
                room_id=None,
                min_duration_minutes=30,
                max_duration_minutes=480,
                max_advance_days=30,
                cancellation_deadline_minutes=60,
                requires_payment=False,
                hold_ttl_seconds=900,
                checkin_open_before_minutes=30,
                geo_radius_meters=150,
            )
            session.add(venue_rule)
        else:
            venue_rule.min_duration_minutes = 30
            venue_rule.max_duration_minutes = 480
            venue_rule.max_advance_days = 30
            venue_rule.cancellation_deadline_minutes = 60
            venue_rule.requires_payment = False
            venue_rule.hold_ttl_seconds = 900
            venue_rule.checkin_open_before_minutes = 30
            venue_rule.geo_radius_meters = 150

        meeting_room_rule = await session.scalar(select(BookingRule).where(BookingRule.room_id == meeting_room.id))
        if meeting_room_rule is None:
            session.add(
                BookingRule(
                    venue_id=venue.id,
                    room_id=meeting_room.id,
                    min_duration_minutes=60,
                    max_duration_minutes=180,
                    max_advance_days=30,
                    cancellation_deadline_minutes=60,
                    requires_payment=False,
                    hold_ttl_seconds=900,
                    checkin_open_before_minutes=30,
                    geo_radius_meters=150,
                )
            )

        role_by_code = {role.code: role for role in (await session.scalars(select(Role))).all()}
        for user_seed in DEMO_USERS:
            user = await _get_or_create_user(user_seed.email, user_seed.name)
            role_code = user_seed.global_role or user_seed.venue_role
            if role_code is None:
                continue
            role = role_by_code[role_code]
            venue_id = venue.id if user_seed.venue_role else None
            assignment = await session.scalar(
                select(UserRoleAssignment).where(
                    UserRoleAssignment.user_id == user.id,
                    UserRoleAssignment.role_id == role.id,
                    UserRoleAssignment.venue_id == venue_id,
                )
            )
            if assignment is None:
                session.add(
                    UserRoleAssignment(
                        user_id=user.id,
                        role_id=role.id,
                        venue_id=venue_id,
                        assigned_by=None,
                    )
                )

        await session.commit()

        seats = (
            await session.scalars(
                select(Seat).join(Room, Seat.room_id == Room.id).where(Room.venue_id == venue.id).order_by(Room.name, Seat.label)
            )
        ).all()

    print("Demo seed completed.")
    print(f"Venue: {DEMO_VENUE_NAME}")
    print(f"Address: {DEMO_VENUE_ADDRESS}")
    print("Accounts:")
    for user_seed in DEMO_USERS:
        role_name = user_seed.global_role or user_seed.venue_role or "none"
        print(f"  - {user_seed.email} / {DEMO_PASSWORD} ({role_name})")
    print("Available seats:")
    for seat in seats:
        print(f"  - {seat.label}")


if __name__ == "__main__":
    asyncio.run(main())
