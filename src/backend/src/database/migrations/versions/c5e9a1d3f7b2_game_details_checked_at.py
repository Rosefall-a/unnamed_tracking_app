"""When a game was last checked for missing artwork and play times, so one that
no site has anything for is not asked about on every run.

Revision ID: c5e9a1d3f7b2
Revises: b3d7f1a9c5e2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "c5e9a1d3f7b2"
down_revision: str | None = "b3d7f1a9c5e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("games", sa.Column("details_checked_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "details_checked_at")
