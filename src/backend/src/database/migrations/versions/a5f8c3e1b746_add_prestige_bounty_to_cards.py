"""add prestige bounty link to cards, drop manual prestige fields

Revision ID: a5f8c3e1b746
Revises: f5c9d3e8b462
Create Date: 2026-09-08

Prestige stops being a manual reason/note the user types in and becomes a
link to a real, system-auto-generated Bounty (see
features/cards/prestige_challenge.py) that the user actually completes
through the existing Bounties flow — the only way to verify a prestige
claim this app has. No data migration needed: prestige_reason and
prestige_challenge_note have never been populated by real user data.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a5f8c3e1b746"
down_revision: Union[str, None] = "f5c9d3e8b462"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("cards", "prestige_reason")
    op.drop_column("cards", "prestige_challenge_note")
    op.add_column(
        "cards",
        sa.Column(
            "bounty_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("bounties.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_cards_bounty_id", "cards", ["bounty_id"])


def downgrade() -> None:
    op.drop_index("ix_cards_bounty_id", table_name="cards")
    op.drop_column("cards", "bounty_id")
    op.add_column("cards", sa.Column("prestige_challenge_note", sa.String(length=500), nullable=True))
    op.add_column("cards", sa.Column("prestige_reason", sa.String(length=30), nullable=True))
