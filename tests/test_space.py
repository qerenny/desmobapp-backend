from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Role, Room, User, UserRoleAssignment

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


async def test_space_endpoints_and_admin_rbac(client: AsyncClient, db_session: AsyncSession) -> None:
    client_login = await _register_and_login(
        client,
        email=f"pytest-client-{uuid4().hex[:8]}@example.com",
        name="Pytest Client",
    )
    admin_login = await _register_and_login(
        client,
        email=f"pytest-admin-{uuid4().hex[:8]}@example.com",
        name="Pytest Admin",
    )

    admin_user = await db_session.scalar(select(User).where(User.email == admin_login["user"]["email"]))
    admin_role = await db_session.scalar(select(Role).where(Role.code == "admin"))
    assert admin_user is not None
    assert admin_role is not None
    db_session.add(UserRoleAssignment(user_id=admin_user.id, role_id=admin_role.id, venue_id=None, assigned_by=None))
    await db_session.commit()
    admin_login = await _login(client, email=admin_login["user"]["email"])

    client_headers = {"Authorization": f"Bearer {client_login['accessToken']}"}
    admin_headers = {"Authorization": f"Bearer {admin_login['accessToken']}"}

    forbidden_response = await client.post(
        "/admin/venues",
        json={"name": "Pytest Forbidden Venue", "address": "No access", "features": []},
        headers=client_headers,
    )
    assert forbidden_response.status_code == 403

    create_venue_response = await client.post(
        "/admin/venues",
        json={"name": f"Pytest Venue {uuid4().hex[:6]}", "address": "Nevsky 1", "features": []},
        headers=admin_headers,
    )
    assert create_venue_response.status_code == 201, create_venue_response.text
    venue_payload = create_venue_response.json()
    venue_id = venue_payload["id"]

    room = Room(
        venue_id=venue_id,
        name="Pytest Room",
        allow_full_room_booking=True,
        grid_width=10,
        grid_height=8,
        status="active",
    )
    db_session.add(room)
    await db_session.commit()
    await db_session.refresh(room)

    layout_response = await client.put(
        f"/admin/rooms/{room.id}/layout",
        json={
            "allowFullRoomBooking": True,
            "seats": [
                {"label": "A-1", "gridX": 1, "gridY": 1, "seatType": "desk", "active": True},
                {"label": "A-2", "gridX": 2, "gridY": 1, "seatType": "desk", "active": True},
            ],
        },
        headers=admin_headers,
    )
    assert layout_response.status_code == 200, layout_response.text
    assert len(layout_response.json()["seats"]) == 2

    venues_response = await client.get("/venues", headers=client_headers)
    assert venues_response.status_code == 200, venues_response.text
    assert any(item["id"] == venue_id for item in venues_response.json())

    venue_details_response = await client.get(f"/venues/{venue_id}", headers=client_headers)
    assert venue_details_response.status_code == 200, venue_details_response.text
    assert venue_details_response.json()["id"] == venue_id

    rooms_response = await client.get(f"/venues/{venue_id}/rooms", headers=client_headers)
    assert rooms_response.status_code == 200, rooms_response.text
    assert len(rooms_response.json()) == 1

    seats_response = await client.get(f"/rooms/{room.id}/seats", headers=client_headers)
    assert seats_response.status_code == 200, seats_response.text
    assert len(seats_response.json()) == 2
