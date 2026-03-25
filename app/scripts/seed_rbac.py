from __future__ import annotations

import asyncio

from app.db.session import SessionLocal
from app.services.rbac import seed_roles_and_permissions


async def main() -> None:
    async with SessionLocal() as session:
        await seed_roles_and_permissions(session)
    print("RBAC seed completed.")


if __name__ == "__main__":
    asyncio.run(main())
