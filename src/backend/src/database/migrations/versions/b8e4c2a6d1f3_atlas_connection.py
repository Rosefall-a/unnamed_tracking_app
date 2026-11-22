"""Add the Atlas metadata node connection to users.

Revision ID: b8e4c2a6d1f3
Revises: a6c3e9f1b7d2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "b8e4c2a6d1f3"
down_revision: str | None = "a6c3e9f1b7d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("users", sa.Column("atlas_base_url", sa.String(512), nullable=True))
    h.add_column_if_missing("users", sa.Column("atlas_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "atlas_token")
    op.drop_column("users", "atlas_base_url")
