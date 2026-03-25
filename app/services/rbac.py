from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import ROLE_NAMES, ROLE_PERMISSIONS, all_permissions
from app.db.models import Permission, Role, RolePermission, UserRoleAssignment


async def seed_roles_and_permissions(session: AsyncSession) -> None:
    permissions_by_code = {
        permission.code: permission
        for permission in (await session.scalars(select(Permission))).all()
    }
    roles_by_code = {role.code: role for role in (await session.scalars(select(Role))).all()}

    for permission_code in all_permissions():
        if permission_code not in permissions_by_code:
            permission = Permission(code=permission_code)
            session.add(permission)
            await session.flush()
            permissions_by_code[permission_code] = permission

    for role_code, role_name in ROLE_NAMES.items():
        if role_code not in roles_by_code:
            role = Role(code=role_code, name=role_name)
            session.add(role)
            await session.flush()
            roles_by_code[role_code] = role

    existing_pairs = {
        (role_id, permission_id)
        for role_id, permission_id in (
            await session.execute(select(RolePermission.role_id, RolePermission.permission_id))
        ).all()
    }

    for role_code, permission_codes in ROLE_PERMISSIONS.items():
        role = roles_by_code[role_code]
        for permission_code in permission_codes:
            permission = permissions_by_code[permission_code]
            pair = (role.id, permission.id)
            if pair not in existing_pairs:
                session.add(RolePermission(role_id=role.id, permission_id=permission.id))
                existing_pairs.add(pair)

    await session.commit()


async def get_user_permissions_context(
    session: AsyncSession,
    user_id: UUID,
) -> tuple[list[str], dict[str, list[str]], list[str]]:
    rows = (
        await session.execute(
            select(Role.code, UserRoleAssignment.venue_id)
            .join(UserRoleAssignment, UserRoleAssignment.role_id == Role.id)
            .where(UserRoleAssignment.user_id == user_id)
        )
    ).all()

    global_roles: list[str] = []
    venue_roles_map: dict[str, list[str]] = defaultdict(list)

    for role_code, venue_id in rows:
        if venue_id is None:
            global_roles.append(role_code)
        else:
            venue_roles_map[str(venue_id)].append(role_code)

    permission_set: set[str] = set()
    for role_code in global_roles:
        permission_set.update(ROLE_PERMISSIONS.get(role_code, set()))
    for role_codes in venue_roles_map.values():
        for role_code in role_codes:
            permission_set.update(ROLE_PERMISSIONS.get(role_code, set()))

    return sorted(set(global_roles)), dict(venue_roles_map), sorted(permission_set)
