"""add external_id to games

Revision ID: f7c2a4e8b1d9
Revises: e4b7c9f1a2d6
Create Date: 2026-09-05

A library-sync provider's own stable id for a game (Steam appid,
RetroAchievements GameID, PSN npCommunicationId) — title alone isn't a
stable identity across re-syncs (Steam occasionally reports a different
display name for the same appid, e.g. briefly appending "- GOTY Edition"),
which was creating duplicate rows for the same real game.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7c2a4e8b1d9"
down_revision: Union[str, None] = "e4b7c9f1a2d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("external_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "external_id")
