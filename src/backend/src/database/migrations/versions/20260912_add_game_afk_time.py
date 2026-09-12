"""add aggregate game AFK time

Revision ID: 20260912_add_game_afk_time
Revises: 20260911_merge_api_key_heads
Create Date: 2026-09-12
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260912_add_game_afk_time"
down_revision: Union[str, None] = "20260911_merge_api_key_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_afk_time",
        sa.Column("game_id", sa.UUID(), nullable=False),
        sa.Column("afk_seconds", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["game_id"], ["games.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("game_id"),
    )
    op.alter_column("game_afk_time", "afk_seconds", server_default=None)


def downgrade() -> None:
    op.drop_table("game_afk_time")
