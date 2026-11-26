"""When a sign-in or an app key was last used, and which browser a sign-in is,
so Settings can list signed-in devices and show stale keys.

Every column is added only when missing: some databases already have
user_agent and last_seen_at on user_sessions from an earlier, reverted change,
and those columns and their values are left exactly as they are.

Revision ID: c9e2a4f6b1d3
Revises: b7d4f2a8c3e1
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from src.database import migration_helpers as h

revision: str = "c9e2a4f6b1d3"
down_revision: str | None = "b7d4f2a8c3e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("user_sessions", sa.Column("user_agent", sa.Text(), nullable=True))
    h.add_column_if_missing(
        "user_sessions", sa.Column("last_seen_at", sa.BigInteger(), nullable=True)
    )
    h.add_column_if_missing(
        "user_api_keys", sa.Column("last_used_at", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    # Only the key column is new for certain; the session columns may predate
    # this revision, so a downgrade leaves them (and their data) in place.
    if h.has_column("user_api_keys", "last_used_at"):
        from alembic import op

        op.drop_column("user_api_keys", "last_used_at")
