"""bounty goal system

Revision ID: b3e8f1c7a962
Revises: f7c1a9e2d453
Create Date: 2026-09-06

Turns Bounties from a per-game freeform note into a standalone personal
goal/challenge system: typed goals (completion/mastery/achievement/
collection/challenge/watch/custom), an optional target (game,
achievement, or named collection — never a copy of that data), three
progress modes, a point reward, and a permanent point-transaction ledger.

There are no existing bounty rows to migrate (the previous iteration's
rows were already cleared in f7c1a9e2d453), so this is a straight
add/rename rather than a backfill.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b3e8f1c7a962"
down_revision: Union[str, None] = "f7c1a9e2d453"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("bounties", "notes", new_column_name="description")
    op.alter_column("bounties", "game_id", nullable=True)

    op.add_column(
        "bounties", sa.Column("type", sa.String(length=20), nullable=False, server_default="custom")
    )
    op.add_column("bounties", sa.Column("difficulty", sa.String(length=10), nullable=True))
    op.add_column(
        "bounties", sa.Column("target_achievement_provider", sa.String(length=30), nullable=True)
    )
    op.add_column(
        "bounties",
        sa.Column("target_achievement_external_id", sa.String(length=200), nullable=True),
    )
    op.add_column(
        "bounties", sa.Column("target_collection_name", sa.String(length=120), nullable=True)
    )
    op.add_column(
        "bounties",
        sa.Column("progress_mode", sa.String(length=12), nullable=False, server_default="binary"),
    )
    op.add_column(
        "bounties",
        sa.Column("progress_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
    )
    op.add_column("bounties", sa.Column("progress_target", sa.Numeric(10, 2), nullable=True))
    op.add_column(
        "bounties", sa.Column("points_reward", sa.BigInteger(), nullable=False, server_default="0")
    )
    op.add_column("bounties", sa.Column("target_date", sa.BigInteger(), nullable=True))
    op.add_column("bounties", sa.Column("started_at", sa.BigInteger(), nullable=True))

    op.create_table(
        "bounty_point_transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "bounty_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bounties.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("reason", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index(
        "ix_bounty_point_transactions_user_id", "bounty_point_transactions", ["user_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_bounty_point_transactions_user_id", table_name="bounty_point_transactions")
    op.drop_table("bounty_point_transactions")

    op.drop_column("bounties", "started_at")
    op.drop_column("bounties", "target_date")
    op.drop_column("bounties", "points_reward")
    op.drop_column("bounties", "progress_target")
    op.drop_column("bounties", "progress_value")
    op.drop_column("bounties", "progress_mode")
    op.drop_column("bounties", "target_collection_name")
    op.drop_column("bounties", "target_achievement_external_id")
    op.drop_column("bounties", "target_achievement_provider")
    op.drop_column("bounties", "difficulty")
    op.drop_column("bounties", "type")

    op.alter_column("bounties", "game_id", nullable=False)
    op.alter_column("bounties", "description", new_column_name="notes")
