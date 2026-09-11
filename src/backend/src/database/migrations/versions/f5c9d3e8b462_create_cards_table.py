"""create cards table

Revision ID: f5c9d3e8b462
Revises: e91b5f3a7c26
Create Date: 2026-09-09

Card as its own first-class entity, per the design spec — separate from
Game so a game can eventually carry more than one card for genuinely
different accomplishments (a normal completion vs. a Prestige challenge
run), each with its own permanent archive_number. A card can optionally
belong to a Set (cards.set_id); games no longer have a direct set link
(see rename_series_to_sets).
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f5c9d3e8b462"
down_revision: Union[str, None] = "e91b5f3a7c26"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "cards",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("archive_number", sa.Integer(), nullable=True),
        sa.Column(
            "set_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sets.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("rarity", sa.String(length=20), nullable=True),
        sa.Column("prestige_reason", sa.String(length=30), nullable=True),
        sa.Column("prestige_challenge_note", sa.String(length=500), nullable=True),
        sa.Column("card_customization", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_cards_user_id", "cards", ["user_id"])
    op.create_index("ix_cards_game_id", "cards", ["game_id"])
    op.create_index("ix_cards_set_id", "cards", ["set_id"])
    op.create_index(
        "ix_cards_archive_number_user_active",
        "cards",
        ["user_id", "archive_number"],
        unique=True,
        postgresql_where=sa.text("archive_number IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_cards_archive_number_user_active", table_name="cards")
    op.drop_index("ix_cards_set_id", table_name="cards")
    op.drop_index("ix_cards_game_id", table_name="cards")
    op.drop_index("ix_cards_user_id", table_name="cards")
    op.drop_table("cards")
