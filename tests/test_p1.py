from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, VenueStatus
from app.db.models import BookingRule, NotificationPreference, Room, RoomHour, Seat, Venue

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_and_login(client: AsyncClient, *, email: str, name: str, password: str = "secret123") -> dict:
    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert register_response.status_code == 201, register_response.text
    login_response = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200, login_response.text
    return login_response.json()


async def _create_bookable_seat(session: AsyncSession) -> tuple[Venue, Room, Seat, date, datetime, datetime]:
    venue = Venue(
        name=f"Pytest P1 Venue {uuid4().hex[:6]}",
        address="P1 Test address",
        timezone="Europe/Moscow",
        status=VenueStatus.ACTIVE,
    )
    session.add(venue)
    await session.flush()

    room = Room(
        venue_id=venue.id,
        name="Pytest P1 Room",
        allow_full_room_booking=True,
        grid_width=8,
        grid_height=8,
        status="active",
    )
    session.add(room)
    await session.flush()

    seat = Seat(
        room_id=room.id,
        label="P1-1",
        grid_x=1,
        grid_y=1,
        seat_type="desk",
        attributes=None,
        active=True,
    )
    session.add(seat)

    target_date = datetime.now(UTC).date() + timedelta(days=2)
    session.add(
        RoomHour(
            room_id=room.id,
            weekday=target_date.weekday(),
            start_local_time=time(9, 0),
            end_local_time=time(21, 0),
            is_closed=False,
        )
    )
    session.add(
        BookingRule(
            room_id=room.id,
            venue_id=venue.id,
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
    await session.commit()
    await session.refresh(seat)

    start_time = datetime.combine(target_date, time(7, 0), tzinfo=UTC)
    end_time = datetime.combine(target_date, time(8, 0), tzinfo=UTC)
    return venue, room, seat, target_date, start_time, end_time


async def test_refresh_logout_profile_and_notification_preferences(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    login_payload = await _register_and_login(
        client,
        email=f"pytest-p1-auth-{uuid4().hex[:8]}@example.com",
        name="Pytest P1 Auth",
    )
    headers = {"Authorization": f"Bearer {login_payload['accessToken']}"}

    me_response = await client.get("/me", headers=headers)
    assert me_response.status_code == 200, me_response.text
    assert me_response.json()["email"] == login_payload["user"]["email"]

    update_profile_response = await client.patch(
        "/me",
        json={"name": "Updated P1 User", "phone": "+79990001122"},
        headers=headers,
    )
    assert update_profile_response.status_code == 200, update_profile_response.text
    assert update_profile_response.json()["name"] == "Updated P1 User"

    prefs_get_response = await client.get("/notifications/preferences", headers=headers)
    assert prefs_get_response.status_code == 200, prefs_get_response.text
    assert prefs_get_response.json() == {
        "emailNotifications": True,
        "pushNotifications": True,
        "reminderBeforeBooking": True,
        "promotionalEmails": False,
    }

    prefs_put_response = await client.put(
        "/notifications/preferences",
        json={"emailNotifications": False, "pushNotifications": True, "reminderBeforeBooking": False},
        headers=headers,
    )
    assert prefs_put_response.status_code == 200, prefs_put_response.text

    prefs_after_update = await client.get("/notifications/preferences", headers=headers)
    assert prefs_after_update.status_code == 200, prefs_after_update.text
    assert prefs_after_update.json()["emailNotifications"] is False
    assert prefs_after_update.json()["reminderBeforeBooking"] is False

    pref_row = await db_session.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_id == UUID(login_payload["user"]["id"])
        )
    )
    assert pref_row is not None
    assert pref_row.email_notifications is False

    refresh_response = await client.post(
        "/auth/refresh",
        json={"refreshToken": login_payload["refreshToken"]},
    )
    assert refresh_response.status_code == 200, refresh_response.text
    refreshed_payload = refresh_response.json()
    assert refreshed_payload["accessToken"]
    assert refreshed_payload["refreshToken"] != login_payload["refreshToken"]

    logout_response = await client.post(
        "/auth/logout",
        json={"refreshToken": refreshed_payload["refreshToken"]},
    )
    assert logout_response.status_code == 200, logout_response.text

    refresh_after_logout = await client.post(
        "/auth/refresh",
        json={"refreshToken": refreshed_payload["refreshToken"]},
    )
    assert refresh_after_logout.status_code == 401


async def test_me_bookings_listing_and_favorites(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    login_payload = await _register_and_login(
        client,
        email=f"pytest-p1-bookings-{uuid4().hex[:8]}@example.com",
        name="Pytest P1 Booking User",
    )
    headers = {"Authorization": f"Bearer {login_payload['accessToken']}"}

    venue, room, seat, target_date, start_time, end_time = await _create_bookable_seat(db_session)

    hold_response = await client.post(
        "/holds",
        json={
            "level": "seat",
            "seatId": str(seat.id),
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert hold_response.status_code == 201, hold_response.text
    hold_id = hold_response.json()["id"]

    booking_response = await client.post(
        "/bookings",
        json={
            "level": "seat",
            "seatId": str(seat.id),
            "holdId": hold_id,
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert booking_response.status_code == 201, booking_response.text
    booking_id = booking_response.json()["id"]

    list_response = await client.get(
        "/me/bookings",
        params={
            "status": BookingStatus.CONFIRMED.value,
            "dateFrom": target_date.isoformat(),
            "dateTo": target_date.isoformat(),
            "page": 1,
            "limit": 10,
        },
        headers=headers,
    )
    assert list_response.status_code == 200, list_response.text
    payload = list_response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == booking_id
    assert payload["items"][0]["venueId"] == str(venue.id)

    alias_list_response = await client.get("/bookings", headers=headers)
    assert alias_list_response.status_code == 200, alias_list_response.text
    assert alias_list_response.json()["total"] >= 1

    empty_favorites_response = await client.get("/favorites", headers=headers)
    assert empty_favorites_response.status_code == 200, empty_favorites_response.text
    assert empty_favorites_response.json() == []

    create_favorite_response = await client.post(
        "/favorites",
        json={"venueId": str(venue.id)},
        headers=headers,
    )
    assert create_favorite_response.status_code == 201, create_favorite_response.text
    assert create_favorite_response.json()["id"] == str(venue.id)

    favorites_response = await client.get("/favorites", headers=headers)
    assert favorites_response.status_code == 200, favorites_response.text
    assert len(favorites_response.json()) == 1
    assert favorites_response.json()[0]["id"] == str(venue.id)

    delete_favorite_response = await client.delete(f"/favorites/{venue.id}", headers=headers)
    assert delete_favorite_response.status_code == 204, delete_favorite_response.text

    favorites_after_delete = await client.get("/favorites", headers=headers)
    assert favorites_after_delete.status_code == 200, favorites_after_delete.text
    assert favorites_after_delete.json() == []
