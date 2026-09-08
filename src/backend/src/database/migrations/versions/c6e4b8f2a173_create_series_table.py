"""create series table

Revision ID: c6e4b8f2a173
Revises: b3f7d2a91c58
Create Date: 2026-09-09

A real, position-aware game grouping (name, optional target_total),
distinct from the existing free-text Game.series string (left untouched)
and the unrelated Collections smart-grouping feature. Games join via the
new games.series_id, nullable, SET NULL on series delete.
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c6e4b8f2a173"
down_revision: Union[str, None] = "b3f7d2a91c58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "series",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_total", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_series_user_id_name"),
    )
    op.create_index("ix_series_user_id", "series", ["user_id"])

    op.add_column(
        "games",
        sa.Column("series_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("series.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_games_series_id", "games", ["series_id"])


def downgrade() -> None:
    op.drop_index("ix_games_series_id", table_name="games")
    op.drop_column("games", "series_id")
    op.drop_index("ix_series_user_id", table_name="series")
    op.drop_table("series")
