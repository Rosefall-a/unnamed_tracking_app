"""add game_platforms table

Revision ID: a7c4d91e2f08
Revises: 1c6f2e8a9b70
Create Date: 2026-09-02

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a7c4d91e2f08"
down_revision: Union[str, None] = "1c6f2e8a9b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_platforms",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("playtime_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("completion_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("last_played_at", sa.BigInteger(), nullable=True),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_game_platforms_game_id", "game_platforms", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_game_platforms_game_id", table_name="game_platforms")
    op.drop_table("game_platforms")
