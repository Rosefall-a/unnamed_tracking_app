"""add PKCE-bound native OIDC handoffs

Revision ID: 20260915_mobile_oidc
Revises: 20260915_user_invitations
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260915_mobile_oidc"
down_revision: Union[str, Sequence[str], None] = "20260915_user_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mobile_oidc_handoffs",
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("verifier_challenge", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("code_hash"),
    )
    op.create_index("ix_mobile_oidc_handoffs_user_id", "mobile_oidc_handoffs", ["user_id"])
    op.create_index("ix_mobile_oidc_handoffs_expires_at", "mobile_oidc_handoffs", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_mobile_oidc_handoffs_expires_at", table_name="mobile_oidc_handoffs")
    op.drop_index("ix_mobile_oidc_handoffs_user_id", table_name="mobile_oidc_handoffs")
    op.drop_table("mobile_oidc_handoffs")
