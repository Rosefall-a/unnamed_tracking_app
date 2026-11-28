"""A game can be set aside: kept, but out of the way (not a real game, online
only, not interested).

Only new, empty columns: every existing game stays exactly as it was, not set
aside.

Revision ID: d8f1a3c5e7b9
Revises: c9e2a4f6b1d3
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from src.database import migration_helpers as h

revision: str = "d8f1a3c5e7b9"
down_revision: str | None = "c9e2a4f6b1d3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("games", sa.Column("set_aside_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing("games", sa.Column("set_aside_reason", sa.String(30), nullable=True))


def downgrade() -> None:
    from alembic import op

    for column in ("set_aside_reason", "set_aside_at"):
        if h.has_column("games", column):
            op.drop_column("games", column)
