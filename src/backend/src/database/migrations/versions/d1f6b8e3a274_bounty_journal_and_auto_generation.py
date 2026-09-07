"""bounty journal and auto-generation

Revision ID: d1f6b8e3a274
Revises: c4d9a2e6f183
Create Date: 2026-09-06

Adds journal entries (a simple dated log per bounty) and an
`auto_generated` flag so a time-gated picker can propose new bounties on
its own without re-suggesting the same target twice.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d1f6b8e3a274"
down_revision: Union[str, None] = "c4d9a2e6f183"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bounties", sa.Column("auto_generated", sa.Boolean(), nullable=False, server_default=sa.false())
    )

    op.create_table(
        "bounty_journal_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bounty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bounties.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_bounty_journal_entries_bounty_id", "bounty_journal_entries", ["bounty_id"])


def downgrade() -> None:
    op.drop_index("ix_bounty_journal_entries_bounty_id", table_name="bounty_journal_entries")
    op.drop_table("bounty_journal_entries")
    op.drop_column("bounties", "auto_generated")
