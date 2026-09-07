"""bounty objectives and evidence

Revision ID: c4d9a2e6f183
Revises: b3e8f1c7a962
Create Date: 2026-09-06

Adds the optional checklist (BountyObjective) and documentation
(BountyEvidence) layers on top of a bounty, plus a purely informational
`required_evidence_kinds` hint on the bounty itself.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4d9a2e6f183"
down_revision: Union[str, None] = "b3e8f1c7a962"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "bounties",
        sa.Column(
            "required_evidence_kinds",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )

    op.create_table(
        "bounty_objectives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bounty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bounties.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("kind", sa.String(length=12), nullable=False, server_default="checkbox"),
        sa.Column("done", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("progress_value", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("progress_target", sa.Numeric(10, 2), nullable=True),
        sa.Column("target_achievement_provider", sa.String(length=30), nullable=True),
        sa.Column("target_achievement_external_id", sa.String(length=200), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_bounty_objectives_bounty_id", "bounty_objectives", ["bounty_id"])

    op.create_table(
        "bounty_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "bounty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("bounties.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(length=12), nullable=False),
        sa.Column(
            "media_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("text", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_bounty_evidence_bounty_id", "bounty_evidence", ["bounty_id"])


def downgrade() -> None:
    op.drop_index("ix_bounty_evidence_bounty_id", table_name="bounty_evidence")
    op.drop_table("bounty_evidence")

    op.drop_index("ix_bounty_objectives_bounty_id", table_name="bounty_objectives")
    op.drop_table("bounty_objectives")

    op.drop_column("bounties", "required_evidence_kinds")
