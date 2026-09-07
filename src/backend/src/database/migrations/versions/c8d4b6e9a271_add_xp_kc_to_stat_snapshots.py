"""add xp, kc to game_profile_stat_snapshots

Revision ID: c8d4b6e9a271
Revises: a3c9e7f215bd
Create Date: 2026-09-06

Raw integers alongside the existing display-string `stats` — lets a
day-to-day "gained this much XP / killed this many" digest be computed
accurately instead of diffing level numbers (a single level can span
tens of thousands of XP).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8d4b6e9a271"
down_revision: Union[str, None] = "a3c9e7f215bd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "game_profile_stat_snapshots", sa.Column("xp", postgresql.JSON(), nullable=False, server_default="{}")
    )
    op.add_column(
        "game_profile_stat_snapshots", sa.Column("kc", postgresql.JSON(), nullable=False, server_default="{}")
    )


def downgrade() -> None:
    op.drop_column("game_profile_stat_snapshots", "kc")
    op.drop_column("game_profile_stat_snapshots", "xp")
