"""add parent_game_id + relationship_type to games (modpack/mod/dlc support)

Revision ID: a7d2e5c8f3b1
Revises: f1a3c7e9b2d4
Create Date: 2026-09-05

A self-referential game tree instead of a boolean is_modded — "modded" and
"DLC/expansion" are related but distinct concepts, and a base game can have
several kinds of variant (GTNH is a MODPACK of Minecraft; Phantom Liberty
is an EXPANSION of Cyberpunk 2077). Each variant is its own full Game row,
so saves/achievements/media already scope correctly to it via their
existing game_id FK — no separate "configuration" layer needed.
relationship_type is a plain string, not a hard DB enum, so new
relationship kinds never need a migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7d2e5c8f3b1"
down_revision: Union[str, None] = "f1a3c7e9b2d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column(
            "parent_game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("games", sa.Column("relationship_type", sa.String(length=30), nullable=True))
    op.create_index("ix_games_parent_game_id", "games", ["parent_game_id"])


def downgrade() -> None:
    op.drop_index("ix_games_parent_game_id", table_name="games")
    op.drop_column("games", "relationship_type")
    op.drop_column("games", "parent_game_id")
