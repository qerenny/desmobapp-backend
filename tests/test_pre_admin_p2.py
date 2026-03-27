from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import BookingStatus, PaymentStatus, VenueStatus
from app.db.models import (
    BookingRule,
    Feature,
    FeatureLink,
    NotificationDevice,
    PasswordResetToken,
    Room,
    RoomHour,
    Seat,
    Tariff,
    Venue,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    name: str,
    password: str = "secret123",
) -> dict:
    register_response = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "name": name},
    )
    assert register_response.status_code == 201, register_response.text

    login_response = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 200, login_response.text
    return login_response.json()


async def _create_configured_space(
    session: AsyncSession,
) -> tuple[Venue, Room, Seat, date, datetime, datetime]:
    venue = Venue(
        name=f"Pytest P2 Venue {uuid4().hex[:6]}",
        address="P2 Test address",
        timezone="Europe/Moscow",
        status=VenueStatus.ACTIVE,
    )
    session.add(venue)
    await session.flush()

    room = Room(
        venue_id=venue.id,
        name="Pytest P2 Room",
        allow_full_room_booking=True,
        grid_width=10,
        grid_height=10,
        status="active",
    )
    session.add(room)
    await session.flush()

    seat = Seat(
        room_id=room.id,
        label="P2-1",
        grid_x=1,
        grid_y=1,
        seat_type="desk",
        attributes={"monitor": True},
        active=True,
    )
    session.add(seat)
    await session.flush()

    feature = Feature(code=f"focus_room_{uuid4().hex[:6]}", name="Focus Room", icon="focus")
    session.add(feature)
    await session.flush()
    session.add(FeatureLink(feature_id=feature.id, room_id=room.id))
    session.add(FeatureLink(feature_id=feature.id, venue_id=venue.id))

    target_date = datetime.now(UTC).date() + timedelta(days=3)
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
    session.add(
        Tariff(
            room_id=room.id,
            venue_id=venue.id,
            seat_id=seat.id,
            billing_unit="hour",
            price_amount_cents=350,
            currency="RUB",
            active_from=target_date,
        )
    )
    await session.commit()
    await session.refresh(seat)

    start_time = datetime.combine(target_date, time(7, 0), tzinfo=UTC)
    end_time = datetime.combine(target_date, time(8, 0), tzinfo=UTC)
    return venue, room, seat, target_date, start_time, end_time


async def _create_booking(
    client: AsyncClient,
    *,
    seat_id: UUID,
    start_time: datetime,
    end_time: datetime,
    headers: dict[str, str],
) -> dict:
    hold_response = await client.post(
        "/holds",
        json={
            "level": "seat",
            "seatId": str(seat_id),
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert hold_response.status_code == 201, hold_response.text

    booking_response = await client.post(
        "/bookings",
        json={
            "level": "seat",
            "seatId": str(seat_id),
            "holdId": hold_response.json()["id"],
            "startTime": start_time.isoformat().replace("+00:00", "Z"),
            "endTime": end_time.isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert booking_response.status_code == 201, booking_response.text
    return booking_response.json()


async def test_password_reset_flow_revokes_previous_sessions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    password = "secret123"
    new_password = "new-secret123"
    login_payload = await _register_and_login(
        client,
        email=f"pytest-p2-auth-{uuid4().hex[:8]}@example.com",
        name="Pytest P2 Auth",
        password=password,
    )

    forgot_response = await client.post(
        "/auth/forgot-password",
        json={"email": login_payload["user"]["email"]},
    )
    assert forgot_response.status_code == 200, forgot_response.text
    forgot_payload = forgot_response.json()
    assert forgot_payload["resetToken"]

    reset_row = await db_session.scalar(
        select(PasswordResetToken).where(
            PasswordResetToken.user_id == UUID(login_payload["user"]["id"])
        )
    )
    assert reset_row is not None

    reset_response = await client.post(
        "/auth/reset-password",
        json={"token": forgot_payload["resetToken"], "newPassword": new_password},
    )
    assert reset_response.status_code == 200, reset_response.text

    refresh_after_reset = await client.post(
        "/auth/refresh",
        json={"refreshToken": login_payload["refreshToken"]},
    )
    assert refresh_after_reset.status_code == 401

    old_password_login = await client.post(
        "/auth/login",
        json={"email": login_payload["user"]["email"], "password": password},
    )
    assert old_password_login.status_code == 401

    new_password_login = await client.post(
        "/auth/login",
        json={"email": login_payload["user"]["email"], "password": new_password},
    )
    assert new_password_login.status_code == 200, new_password_login.text


async def test_booking_extensions_and_notification_inbox(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    login_payload = await _register_and_login(
        client,
        email=f"pytest-p2-bookings-{uuid4().hex[:8]}@example.com",
        name="Pytest P2 Booking User",
    )
    headers = {"Authorization": f"Bearer {login_payload['accessToken']}"}

    _, _, seat, _, start_time, end_time = await _create_configured_space(db_session)
    booking_payload = await _create_booking(
        client,
        seat_id=seat.id,
        start_time=start_time,
        end_time=end_time,
        headers=headers,
    )

    notifications_response = await client.get("/notifications", headers=headers)
    assert notifications_response.status_code == 200, notifications_response.text
    notification_payload = notifications_response.json()
    assert notification_payload["total"] >= 1
    assert any(item["templateCode"] == "booking_created" for item in notification_payload["items"])

    reschedule_response = await client.patch(
        f"/bookings/{booking_payload['id']}/reschedule",
        json={
            "startTime": (start_time + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
            "endTime": (end_time + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert reschedule_response.status_code == 200, reschedule_response.text
    assert reschedule_response.json()["status"] == BookingStatus.CONFIRMED.value

    repeat_response = await client.post(
        f"/bookings/{booking_payload['id']}/repeat",
        json={
            "startTime": (start_time + timedelta(hours=3)).isoformat().replace("+00:00", "Z"),
            "endTime": (end_time + timedelta(hours=3)).isoformat().replace("+00:00", "Z"),
        },
        headers=headers,
    )
    assert repeat_response.status_code == 200, repeat_response.text
    repeated_booking = repeat_response.json()

    cancel_response = await client.delete(
        f"/bookings/{repeated_booking['id']}",
        headers=headers,
    )
    assert cancel_response.status_code == 204, cancel_response.text

    history_response = await client.get("/bookings/history", headers=headers)
    assert history_response.status_code == 200, history_response.text
    history_payload = history_response.json()
    assert history_payload["total"] >= 1
    assert any(item["id"] == repeated_booking["id"] for item in history_payload["items"])


async def test_space_readonly_push_devices_and_payment_extensions(
    client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    login_payload = await _register_and_login(
        client,
        email=f"pytest-p2-space-{uuid4().hex[:8]}@example.com",
        name="Pytest P2 Space User",
    )
    headers = {"Authorization": f"Bearer {login_payload['accessToken']}"}

    venue, room, seat, _, start_time, end_time = await _create_configured_space(db_session)

    room_response = await client.get(f"/rooms/{room.id}", headers=headers)
    assert room_response.status_code == 200, room_response.text
    assert room_response.json()["id"] == str(room.id)

    features_response = await client.get("/features", headers=headers)
    assert features_response.status_code == 200, features_response.text
    assert any(item["name"] == "Focus Room" for item in features_response.json())

    room_hours_response = await client.get(f"/room-hours/{room.id}", headers=headers)
    assert room_hours_response.status_code == 200, room_hours_response.text
    assert len(room_hours_response.json()) == 1

    tariffs_response = await client.get("/tariffs", params={"roomId": str(room.id)}, headers=headers)
    assert tariffs_response.status_code == 200, tariffs_response.text
    assert tariffs_response.json()[0]["roomId"] == str(room.id)

    booking_rule_response = await client.get(
        "/booking-rules/room",
        params={"roomId": str(room.id)},
        headers=headers,
    )
    assert booking_rule_response.status_code == 200, booking_rule_response.text
    assert booking_rule_response.json()["roomId"] == str(room.id)

    device_response = await client.post(
        "/devices/push-tokens",
        json={"platform": "ios", "pushToken": f"push_{uuid4().hex}"},
        headers=headers,
    )
    assert device_response.status_code == 201, device_response.text
    device_id = device_response.json()["id"]

    device_row = await db_session.scalar(select(NotificationDevice).where(NotificationDevice.id == UUID(device_id)))
    assert device_row is not None

    delete_device_response = await client.delete(f"/devices/push-tokens/{device_id}", headers=headers)
    assert delete_device_response.status_code == 204, delete_device_response.text

    booking_payload = await _create_booking(
        client,
        seat_id=seat.id,
        start_time=start_time,
        end_time=end_time,
        headers=headers,
    )
    payment_response = await client.post(
        "/payments",
        json={
            "bookingId": booking_payload["id"],
            "amountCents": 500,
            "currency": "RUB",
            "provider": "mock",
        },
        headers=headers,
    )
    assert payment_response.status_code == 201, payment_response.text
    transaction = payment_response.json()

    get_payment_response = await client.get(f"/payments/{transaction['id']}", headers=headers)
    assert get_payment_response.status_code == 200, get_payment_response.text
    assert get_payment_response.json()["id"] == transaction["id"]

    capture_response = await client.post(f"/payments/{transaction['id']}/capture", headers=headers)
    assert capture_response.status_code == 200, capture_response.text
    assert capture_response.json()["status"] == PaymentStatus.CAPTURED.value

    refund_response = await client.post(
        f"/payments/{transaction['id']}/refund",
        json={"amountCents": 100},
        headers=headers,
    )
    assert refund_response.status_code == 200, refund_response.text
    assert refund_response.json()["refundedCents"] == 100

    webhook_response = await client.post(
        "/payments/webhooks/mock",
        json={"event": "payment.refunded", "transactionId": transaction["id"]},
    )
    assert webhook_response.status_code == 200, webhook_response.text
    assert "Mock webhook accepted" in webhook_response.json()["message"]

    venue_response = await client.get(f"/venues/{venue.id}", headers=headers)
    assert venue_response.status_code == 200, venue_response.text
    assert venue_response.json()["id"] == str(venue.id)
