from __future__ import annotations

from datetime import UTC, date, datetime, time
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import HoldStatus, VenueStatus
from app.db.models import (
    Booking,
    BookingRule,
    Hold,
    NotificationPreference,
    Role,
    Room,
    RoomHour,
    Seat,
    User,
    UserRoleAssignment,
    Venue,
)

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


async def _login(client: AsyncClient, *, email: str, password: str = "secret123") -> dict:
    response = await client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()


async def test_booking_flow_checkin_payment_notifications_and_analytics(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    client_login = await _register_and_login(
        client,
        email=f"pytest-booking-client-{uuid4().hex[:8]}@example.com",
        name="Pytest Booking Client",
    )
    admin_login = await _register_and_login(
        client,
        email=f"pytest-booking-admin-{uuid4().hex[:8]}@example.com",
        name="Pytest Booking Admin",
    )

    admin_user = await db_session.scalar(select(User).where(User.email == admin_login["user"]["email"]))
    client_user = await db_session.scalar(select(User).where(User.email == client_login["user"]["email"]))
    admin_role = await db_session.scalar(select(Role).where(Role.code == "admin"))
    assert admin_user is not None
    assert client_user is not None
    assert admin_role is not None
    db_session.add(UserRoleAssignment(user_id=admin_user.id, role_id=admin_role.id, venue_id=None, assigned_by=None))
    await db_session.commit()
    admin_login = await _login(client, email=admin_login["user"]["email"])

    venue = Venue(
        name=f"Pytest Booking Venue {uuid4().hex[:6]}",
        address="Test address",
        timezone="Europe/Moscow",
        status=VenueStatus.ACTIVE,
    )
    db_session.add(venue)
    await db_session.flush()

    room = Room(
        venue_id=venue.id,
        name="Pytest Booking Room",
        allow_full_room_booking=True,
        grid_width=8,
        grid_height=8,
        status="active",
    )
    db_session.add(room)
    await db_session.flush()

    seat = Seat(
        room_id=room.id,
        label="B-1",
        grid_x=1,
        grid_y=1,
        seat_type="desk",
        attributes=None,
        active=True,
    )
    db_session.add(seat)
    db_session.add(
        RoomHour(
            room_id=room.id,
            weekday=0,
            start_local_time=time(9, 0),
            end_local_time=time(12, 0),
            is_closed=False,
        )
    )
    db_session.add(
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
    await db_session.commit()
    await db_session.refresh(seat)

    client_headers = {"Authorization": f"Bearer {client_login['accessToken']}"}
    admin_headers = {"Authorization": f"Bearer {admin_login['accessToken']}"}

    target_date = date(2026, 3, 30)
    start_time = datetime(2026, 3, 30, 7, 0, tzinfo=UTC)
    end_time = datetime(2026, 3, 30, 8, 0, tzinfo=UTC)

    availability_response = await client.get(
        "/availability",
        params={"level": "seat", "seatId": str(seat.id), "date": target_date.isoformat(), "durationMinutes": 60},
        headers=client_headers,
    )
    assert availability_response.status_code == 200, availability_response.text
    assert [slot["available"] for slot in availability_response.json()["timeSlots"]] == [True, True, True]

    hold_response = await client.post(
        "/holds",
        json={
            "level": "seat",
            "seatId": str(seat.id),
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=client_headers,
    )
    assert hold_response.status_code == 201, hold_response.text
    hold_id = hold_response.json()["id"]

    conflict_hold_response = await client.post(
        "/holds",
        json={
            "level": "seat",
            "seatId": str(seat.id),
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=client_headers,
    )
    assert conflict_hold_response.status_code == 409

    booking_response = await client.post(
        "/bookings",
        json={
            "level": "seat",
            "seatId": str(seat.id),
            "holdId": hold_id,
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=client_headers,
    )
    assert booking_response.status_code == 201, booking_response.text
    booking_payload = booking_response.json()
    booking_id = booking_payload["id"]

    hold = await db_session.scalar(select(Hold).where(Hold.id == hold_id))
    assert hold is not None
    assert hold.status == HoldStatus.CONVERTED

    get_booking_response = await client.get(f"/bookings/{booking_id}", headers=client_headers)
    assert get_booking_response.status_code == 200
    assert get_booking_response.json()["id"] == booking_id

    availability_blocked_response = await client.get(
        "/availability",
        params={"level": "seat", "seatId": str(seat.id), "date": target_date.isoformat(), "durationMinutes": 60},
        headers=client_headers,
    )
    assert availability_blocked_response.status_code == 200
    assert [slot["available"] for slot in availability_blocked_response.json()["timeSlots"]] == [True, False, True]

    checkin_response = await client.post(
        f"/bookings/{booking_id}/checkin",
        json={"method": "geo", "lat": 59.9386, "lon": 30.3141},
        headers=client_headers,
    )
    assert checkin_response.status_code == 200, checkin_response.text
    assert checkin_response.json()["bookingId"] == booking_id

    booking = await db_session.scalar(select(Booking).where(Booking.id == booking_id))
    assert booking is not None
    booking.price_amount_cents = 1500
    await db_session.commit()

    payment_response = await client.post(
        "/payments",
        json={"bookingId": booking_id, "amountCents": 1500, "currency": "RUB", "provider": "mock"},
        headers=client_headers,
    )
    assert payment_response.status_code == 201, payment_response.text
    assert payment_response.json()["status"] == "captured"

    prefs_response = await client.put(
        "/notifications/preferences",
        json={"emailNotifications": False, "pushNotifications": True, "reminderBeforeBooking": False},
        headers=client_headers,
    )
    assert prefs_response.status_code == 200, prefs_response.text
    prefs = await db_session.get(NotificationPreference, client_user.id)
    assert prefs is not None
    assert prefs.email_notifications is False
    assert prefs.reminder_before_booking is False

    analytics_response = await client.get(
        "/admin/analytics/occupancy",
        params={"startDate": target_date.isoformat(), "endDate": target_date.isoformat()},
        headers=admin_headers,
    )
    assert analytics_response.status_code == 200, analytics_response.text
    assert analytics_response.json()["totalBookings"] >= 1

    cancel_booking_response = await client.delete(f"/bookings/{booking_id}", headers=client_headers)
    assert cancel_booking_response.status_code == 204

    availability_after_cancel = await client.get(
        "/availability",
        params={"level": "seat", "seatId": str(seat.id), "date": target_date.isoformat(), "durationMinutes": 60},
        headers=client_headers,
    )
    assert availability_after_cancel.status_code == 200
    assert [slot["available"] for slot in availability_after_cancel.json()["timeSlots"]] == [True, True, True]
