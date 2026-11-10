"""The Old School RuneScape stat sync is taken out.

It kept a per-game switch and a per-account username. Both go; the stats and
stat history an account already has stay as they are.

Revision ID: f4b8d2e6a1c9
Revises: e3a7c9b1d5f4
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "f4b8d2e6a1c9"
down_revision: str | None = "e3a7c9b1d5f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if h.has_column("games", "osrs_stats_enabled"):
        op.drop_column("games", "osrs_stats_enabled")
    if h.has_column("game_profiles", "wiseoldman_username"):
        op.drop_column("game_profiles", "wiseoldman_username")


def downgrade() -> None:
    h.add_column_if_missing(
        "game_profiles", sa.Column("wiseoldman_username", sa.String(64), nullable=True)
    )
    h.add_column_if_missing(
        "games",
        sa.Column(
            "osrs_stats_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
