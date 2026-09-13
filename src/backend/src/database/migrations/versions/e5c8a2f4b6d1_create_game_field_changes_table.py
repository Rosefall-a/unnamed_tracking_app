"""create game_field_changes table

Revision ID: e5c8a2f4b6d1
Revises: d1f6b8e3a274
Create Date: 2026-09-07

A per-field audit trail for a game's metadata (developer, publisher, tags,
description, and the other fields a scan/refresh can overwrite). Written
by update_game whenever one of those fields actually changes value, read
back by the new "History" tab on the game page.
"""

from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5c8a2f4b6d1"
down_revision: Union[str, None] = "d1f6b8e3a274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_field_changes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("field_name", sa.String(length=50), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_game_field_changes_game_id", "game_field_changes", ["game_id"])


def downgrade() -> None:
    op.drop_index("ix_game_field_changes_game_id", table_name="game_field_changes")
    op.drop_table("game_field_changes")
