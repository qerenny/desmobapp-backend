from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import VenueStatus
from app.db.models import Room, Seat, Tariff, Venue
from app.db.session import SessionLocal

DEFAULT_CURRENCY = "RUB"
DEFAULT_ACTIVE_FROM = date.today()


@dataclass(frozen=True)
class TariffDefaults:
    venue_daily_cents: int = 12000
    room_hourly_cents: int = 1800
    seat_hourly_cents: int = 350


DEFAULTS = TariffDefaults()


async def _find_existing_tariff(
    session: AsyncSession,
    *,
    venue_id,
    room_id,
    seat_id,
    billing_unit: str,
    currency: str,
    active_from: date,
) -> Tariff | None:
    stmt = select(Tariff).where(
        Tariff.billing_unit == billing_unit,
        Tariff.currency == currency,
        Tariff.active_from == active_from,
        Tariff.archived_at.is_(None),
    )
    if venue_id is None:
        stmt = stmt.where(Tariff.venue_id.is_(None))
    else:
        stmt = stmt.where(Tariff.venue_id == venue_id)
    if room_id is None:
        stmt = stmt.where(Tariff.room_id.is_(None))
    else:
        stmt = stmt.where(Tariff.room_id == room_id)
    if seat_id is None:
        stmt = stmt.where(Tariff.seat_id.is_(None))
    else:
        stmt = stmt.where(Tariff.seat_id == seat_id)
    return await session.scalar(stmt.order_by(Tariff.id.desc()))


async def _upsert_tariff(
    session: AsyncSession,
    *,
    venue_id,
    room_id,
    seat_id,
    billing_unit: str,
    price_amount_cents: int,
    currency: str = DEFAULT_CURRENCY,
    active_from: date = DEFAULT_ACTIVE_FROM,
) -> bool:
    tariff = await _find_existing_tariff(
        session,
        venue_id=venue_id,
        room_id=room_id,
        seat_id=seat_id,
        billing_unit=billing_unit,
        currency=currency,
        active_from=active_from,
    )
    if tariff is None:
        session.add(
            Tariff(
                venue_id=venue_id,
                room_id=room_id,
                seat_id=seat_id,
                billing_unit=billing_unit,
                price_amount_cents=price_amount_cents,
                currency=currency,
                active_from=active_from,
                archived_at=None,
            )
        )
        return True

    tariff.price_amount_cents = price_amount_cents
    tariff.currency = currency
    tariff.active_from = active_from
    tariff.archived_at = None
    return False


async def main() -> None:
    created_count = 0
    updated_count = 0

    async with SessionLocal() as session:
        venues = (
            await session.scalars(
                select(Venue).where(Venue.status == VenueStatus.ACTIVE).order_by(Venue.name)
            )
        ).all()

        if not venues:
            print("No active venues found. Nothing to seed.")
            return

        for venue in venues:
            if await _upsert_tariff(
                session,
                venue_id=venue.id,
                room_id=None,
                seat_id=None,
                billing_unit="day",
                price_amount_cents=DEFAULTS.venue_daily_cents,
            ):
                created_count += 1
            else:
                updated_count += 1

            rooms = (
                await session.scalars(
                    select(Room).where(Room.venue_id == venue.id, Room.status == "active").order_by(Room.name)
                )
            ).all()
            for room in rooms:
                if room.allow_full_room_booking:
                    if await _upsert_tariff(
                        session,
                        venue_id=venue.id,
                        room_id=room.id,
                        seat_id=None,
                        billing_unit="hour",
                        price_amount_cents=DEFAULTS.room_hourly_cents,
                    ):
                        created_count += 1
                    else:
                        updated_count += 1

                seats = (
                    await session.scalars(
                        select(Seat).where(Seat.room_id == room.id, Seat.active.is_(True)).order_by(Seat.label)
                    )
                ).all()
                for seat in seats:
                    if await _upsert_tariff(
                        session,
                        venue_id=venue.id,
                        room_id=room.id,
                        seat_id=seat.id,
                        billing_unit="hour",
                        price_amount_cents=DEFAULTS.seat_hourly_cents,
                    ):
                        created_count += 1
                    else:
                        updated_count += 1

        await session.commit()

    print("Tariff seed completed.")
    print(f"Active from: {DEFAULT_ACTIVE_FROM.isoformat()}")
    print(f"Created: {created_count}")
    print(f"Updated: {updated_count}")
    print(f"Defaults: venue/day={DEFAULTS.venue_daily_cents} {DEFAULT_CURRENCY}, room/hour={DEFAULTS.room_hourly_cents} {DEFAULT_CURRENCY}, seat/hour={DEFAULTS.seat_hourly_cents} {DEFAULT_CURRENCY}")


if __name__ == "__main__":
    asyncio.run(main())
