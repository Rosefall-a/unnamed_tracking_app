"""create game_file_items

Revision ID: a8d2e6f4c913
Revises: f2c8a5e3b719
Create Date: 2026-09-05

Docs/manuals and modpacks were the last file category in the app still
tracked purely on disk with no DB row and no soft-delete — deleting one
was instant and permanent, the same gap every other delete path here has
already been closed for. This gives each file a row (real created_at,
plus deleted_at for the same 7-day trash pattern as inbox_items).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a8d2e6f4c913"
down_revision: Union[str, None] = "f2c8a5e3b719"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_file_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("games.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_game_file_items_game_id", "game_file_items", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_game_file_items_game_id", table_name="game_file_items")
    op.drop_table("game_file_items")
