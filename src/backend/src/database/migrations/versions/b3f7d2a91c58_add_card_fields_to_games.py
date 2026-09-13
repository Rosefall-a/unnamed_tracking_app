"""add card fields to games

Revision ID: b3f7d2a91c58
Revises: e5c8a2f4b6d1
Create Date: 2026-09-09

Collector Card state: a permanent per-user card_number assigned once (never
reassigned, even across a full redesign), a manual rarity tier, an optional
prestige reason + free-text challenge note (a second, deliberate card for a
harder self-imposed run, never auto-detected), and one JSONB blob holding
template/back-template/accent/border/face/symbol choices so new
customization knobs are a frontend-only change later.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3f7d2a91c58"
down_revision: Union[str, None] = "e5c8a2f4b6d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("card_number", sa.Integer(), nullable=True))
    op.add_column("games", sa.Column("card_generated_at", sa.BigInteger(), nullable=True))
    op.add_column("games", sa.Column("rarity", sa.String(length=20), nullable=True))
    op.add_column("games", sa.Column("prestige_reason", sa.String(length=30), nullable=True))
    op.add_column(
        "games", sa.Column("prestige_challenge_note", sa.String(length=500), nullable=True)
    )
    op.add_column("games", sa.Column("card_customization", postgresql.JSONB(), nullable=True))
    op.create_index(
        "ix_games_card_number_user_active",
        "games",
        ["user_id", "card_number"],
        unique=True,
        postgresql_where=sa.text("card_number IS NOT NULL AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_games_card_number_user_active", table_name="games")
    op.drop_column("games", "card_customization")
    op.drop_column("games", "prestige_challenge_note")
    op.drop_column("games", "prestige_reason")
    op.drop_column("games", "rarity")
    op.drop_column("games", "card_generated_at")
    op.drop_column("games", "card_number")
