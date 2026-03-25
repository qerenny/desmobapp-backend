"""Initial schema.

Revision ID: 20260325_0001
Revises:
Create Date: 2026-03-25 00:00:00
"""

from __future__ import annotations

from alembic import op
from app.db.base import Base
from app.db.models import *  # noqa: F403

# revision identifiers, used by Alembic.
revision = "20260325_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
