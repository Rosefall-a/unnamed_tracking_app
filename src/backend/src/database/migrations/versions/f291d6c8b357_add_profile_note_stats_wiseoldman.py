"""add game_profiles.note, stats, wiseoldman_username

Revision ID: f291d6c8b357
Revises: e7b3f912a4c6
Create Date: 2026-09-06

Backs the new Accounts tab: a short free-text note per account, a
free-form stats key/value list (manually entered or filled by a
WiseOldMan sync for OSRS accounts), and the RuneScape username used for
that sync.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f291d6c8b357"
down_revision: Union[str, None] = "e7b3f912a4c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_profiles", sa.Column("note", sa.Text(), nullable=True))
    op.add_column(
        "game_profiles", sa.Column("stats", postgresql.JSON(), nullable=False, server_default="{}")
    )
    op.add_column("game_profiles", sa.Column("wiseoldman_username", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("game_profiles", "wiseoldman_username")
    op.drop_column("game_profiles", "stats")
    op.drop_column("game_profiles", "note")
