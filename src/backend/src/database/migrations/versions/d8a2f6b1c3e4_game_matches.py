"""Add game_matches: pairs of entries that may be the same game.

revision: d8a2f6b1c3e4
down_revision: e7b3c9d1a5f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "d8a2f6b1c3e4"
down_revision: str | None = "e7b3c9d1a5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.create_table_if_missing(
        "game_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "original_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "steam_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(12), nullable=False, server_default="pending"),
        sa.Column("prefer", sa.String(8), nullable=True),
        sa.Column("undo", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("resolved_at", sa.BigInteger(), nullable=True),
        sa.UniqueConstraint("original_id", "steam_id", name="uq_game_matches_pair"),
    )


def downgrade() -> None:
    op.drop_table("game_matches")
