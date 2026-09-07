"""add stale_since, game_profiles, game_checklist_items, media profile_id

Revision ID: c1f9b3d7e582
Revises: a8d2e6f4c913
Create Date: 2026-09-06

A library sync (Steam/RetroAchievements/PlayStation) only ever adds or
updates games, never removes one that's dropped out of the account's
current library pull. games.stale_since lets a sync flag that instead of
silently leaving a phantom entry or silently deleting real data.

game_profiles + game_checklist_items back the new per-account checklist
and screenshot-scoping feature (e.g. separate OSRS accounts under one
game) without needing a full separate Game row per account.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1f9b3d7e582"
down_revision: Union[str, None] = "a8d2e6f4c913"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("stale_since", sa.BigInteger(), nullable=True))

    op.create_table(
        "game_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_game_profiles_game_id", "game_profiles", ["game_id"])

    op.create_table(
        "game_checklist_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_profiles.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sort_order", sa.Float(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_game_checklist_items_game_id", "game_checklist_items", ["game_id"])
    op.create_index("ix_game_checklist_items_profile_id", "game_checklist_items", ["profile_id"])

    op.add_column(
        "media_items",
        sa.Column(
            "profile_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_profiles.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("media_items", "profile_id")
    op.drop_index("ix_game_checklist_items_profile_id", table_name="game_checklist_items")
    op.drop_index("ix_game_checklist_items_game_id", table_name="game_checklist_items")
    op.drop_table("game_checklist_items")
    op.drop_index("ix_game_profiles_game_id", table_name="game_profiles")
    op.drop_table("game_profiles")
    op.drop_column("games", "stale_since")
