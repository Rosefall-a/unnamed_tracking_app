"""add achievements table and library-sync credentials

Revision ID: f2c8a4e6d1b7
Revises: e7f3b2a1c9d4
Create Date: 2026-09-04

This migration continues from the existing provider-order migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f2c8a4e6d1b7"
down_revision: Union[str, None] = "e7f3b2a1c9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("steam_id", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("steam_api_key", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("retroachievements_username", sa.String(64), nullable=True))

    op.create_table(
        "achievements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("external_id", sa.String(200), nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("icon_url", sa.Text(), nullable=True),
        sa.Column("unlocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("unlocked_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_achievements_game_id", "achievements", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_achievements_game_id", table_name="achievements")
    op.drop_table("achievements")
    op.drop_column("users", "retroachievements_username")
    op.drop_column("users", "steam_api_key")
    op.drop_column("users", "steam_id")
