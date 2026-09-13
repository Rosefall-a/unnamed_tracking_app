"""add deployment OIDC settings table

Revision ID: c3e7f1a9b2d4
Revises: 20260911_merge_api_key_heads
Create Date: 2026-09-13
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3e7f1a9b2d4"
down_revision: Union[str, None] = "20260911_merge_api_key_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "oidc_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("issuer_url", sa.Text(), nullable=True),
        sa.Column("client_id", sa.String(length=256), nullable=True),
        sa.Column("client_secret", sa.Text(), nullable=True),
        sa.Column("scopes", sa.Text(), nullable=False, server_default="openid profile email"),
        sa.Column("redirect_uri", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("oidc_settings")
