"""create game_profile_stat_snapshots

Revision ID: a3c9e7f215bd
Revises: f291d6c8b357
Create Date: 2026-09-06

Dated history of GameProfile.stats — written on every stats change (a
WiseOldMan sync or a manual edit) plus backfilled from WiseOldMan's own
snapshot history on first sync, so progression can be shown over time.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a3c9e7f215bd"
down_revision: Union[str, None] = "f291d6c8b357"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_profile_stat_snapshots",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stats", postgresql.JSON(), nullable=False, server_default="{}"),
        sa.Column("recorded_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_game_profile_stat_snapshots_profile_id", "game_profile_stat_snapshots", ["profile_id"])
    op.create_index("ix_game_profile_stat_snapshots_recorded_at", "game_profile_stat_snapshots", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_game_profile_stat_snapshots_recorded_at", table_name="game_profile_stat_snapshots")
    op.drop_index("ix_game_profile_stat_snapshots_profile_id", table_name="game_profile_stat_snapshots")
    op.drop_table("game_profile_stat_snapshots")
