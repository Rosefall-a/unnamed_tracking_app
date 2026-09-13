"""drop card fields from games

Revision ID: d4a8e6c2f951
Revises: c6e4b8f2a173
Create Date: 2026-09-09

Reverts the Phase-4 shortcut of putting Collector Card state directly on
Game. Card becomes its own table (see create_cards_table) so a game can
eventually have more than one card for genuinely different accomplishments,
and so card data stays separate from game data per the design spec. No
real user data exists in these columns yet (feature just shipped), so this
is a clean drop, not a data migration.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4a8e6c2f951"
down_revision: Union[str, None] = "c6e4b8f2a173"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_games_card_number_user_active", table_name="games")
    op.drop_column("games", "card_customization")
    op.drop_column("games", "prestige_challenge_note")
    op.drop_column("games", "prestige_reason")
    op.drop_column("games", "rarity")
    op.drop_column("games", "card_generated_at")
    op.drop_column("games", "card_number")


def downgrade() -> None:
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
