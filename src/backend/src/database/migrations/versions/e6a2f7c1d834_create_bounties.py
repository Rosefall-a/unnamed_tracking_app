"""create bounties

Revision ID: e6a2f7c1d834
Revises: d5f8a1c3b924
Create Date: 2026-09-06

A light nudge to go back to a dropped/on-hold game — no points, no
stakes, one active bounty at a time, proposed lazily rather than by a
scheduled job.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e6a2f7c1d834"
down_revision: Union[str, None] = "d5f8a1c3b924"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bounties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
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
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_bounties_user_id", "bounties", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_bounties_user_id", table_name="bounties")
    op.drop_table("bounties")
