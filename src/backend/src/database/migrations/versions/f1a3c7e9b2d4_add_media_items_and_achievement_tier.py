"""create media_items table, add achievements.tier

Revision ID: f1a3c7e9b2d4
Revises: e2b8f4d1a6c9
Create Date: 2026-09-09

Screenshots/clips/soundtrack files had no database presence at all (a
directory listing was the entire "model") — no way to tag them, note them,
or link them to a specific achievement. media_items is that missing row.
achievements.tier captures RetroAchievements' progression/missable/
win_condition classification, previously discarded on import.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f1a3c7e9b2d4"
down_revision: Union[str, None] = "e2b8f4d1a6c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "media_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=False),
        sa.Column("tags", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "linked_achievement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("achievements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_media_items_game_id", "media_items", ["game_id"])
    op.add_column("achievements", sa.Column("tier", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("achievements", "tier")
    op.drop_index("ix_media_items_game_id", table_name="media_items")
    op.drop_table("media_items")
