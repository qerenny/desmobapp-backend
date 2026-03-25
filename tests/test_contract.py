from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import UserStatus
from app.db.models import User

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


async def test_openapi_contains_expected_paths_and_security(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    expected_paths = {
        "/auth/login",
        "/auth/register",
        "/venues",
        "/venues/{venueId}",
        "/venues/{venueId}/rooms",
        "/rooms/{roomId}/seats",
        "/availability",
        "/holds",
        "/holds/{holdId}",
        "/bookings",
        "/bookings/{bookingId}",
        "/bookings/{bookingId}/checkin",
        "/payments",
        "/notifications/preferences",
        "/admin/venues",
        "/admin/rooms/{roomId}/layout",
        "/admin/analytics/occupancy",
    }

    assert expected_paths.issubset(set(payload["paths"]))
    assert any(tag["name"] == "Bookings" for tag in payload["tags"])
    schemes = payload["components"]["securitySchemes"].values()
    assert any(scheme.get("type") == "http" and scheme.get("scheme") == "bearer" for scheme in schemes)

async def test_error_format_cors_and_inactive_user_block(client: AsyncClient, db_session: AsyncSession) -> None:
    unauthenticated_response = await client.get("/venues")
    assert unauthenticated_response.status_code == 401
    assert unauthenticated_response.json() == {"detail": "Not authenticated"}

    validation_response = await client.post(
        "/auth/register",
        json={"email": "broken", "password": "123", "name": ""},
    )
    assert validation_response.status_code == 422
    assert isinstance(validation_response.json()["detail"], list)

    cors_response = await client.get("/health/live", headers={"Origin": "http://localhost:3000"})
    assert cors_response.status_code == 200
    assert cors_response.headers["access-control-allow-origin"] == "http://localhost:3000"

    login_payload = await _register_and_login(
        client,
        email=f"pytest-inactive-{uuid4().hex[:8]}@example.com",
        name="Pytest Inactive",
    )
    user = await db_session.scalar(select(User).where(User.email == login_payload["user"]["email"]))
    assert user is not None
    user.status = UserStatus.SUSPENDED
    await db_session.commit()

    blocked_response = await client.get(
        "/venues",
        headers={"Authorization": f"Bearer {login_payload['accessToken']}"},
    )
    assert blocked_response.status_code == 403
    assert blocked_response.json() == {"detail": "User is not active."}
