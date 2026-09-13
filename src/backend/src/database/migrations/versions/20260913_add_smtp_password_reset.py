"""add SMTP settings and password reset tokens

Revision ID: 20260913_smtp_reset
Revises: 20260913_oidc_providers
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_smtp_reset"
down_revision: Union[str, None] = "20260913_oidc_providers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_integration_settings", sa.Column("smtp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("app_integration_settings", sa.Column("smtp_host", sa.String(length=255), nullable=True))
    op.add_column("app_integration_settings", sa.Column("smtp_port", sa.Integer(), nullable=False, server_default="587"))
    op.add_column("app_integration_settings", sa.Column("smtp_username", sa.String(length=320), nullable=True))
    op.add_column("app_integration_settings", sa.Column("smtp_password", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("smtp_use_tls", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("app_integration_settings", sa.Column("smtp_use_ssl", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("app_integration_settings", sa.Column("smtp_from_email", sa.String(length=320), nullable=True))
    op.add_column("app_integration_settings", sa.Column("smtp_from_name", sa.String(length=200), nullable=True))
    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.BigInteger(), nullable=False),
        sa.Column("used_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_password_reset_tokens_user_id", "password_reset_tokens", ["user_id"])
    op.create_index("ix_password_reset_tokens_token_hash", "password_reset_tokens", ["token_hash"])
    op.create_index("ix_password_reset_tokens_expires_at", "password_reset_tokens", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_password_reset_tokens_expires_at", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_token_hash", table_name="password_reset_tokens")
    op.drop_index("ix_password_reset_tokens_user_id", table_name="password_reset_tokens")
    op.drop_table("password_reset_tokens")
    for column in ("smtp_from_name", "smtp_from_email", "smtp_use_ssl", "smtp_use_tls", "smtp_password", "smtp_username", "smtp_port", "smtp_host", "smtp_enabled"):
        op.drop_column("app_integration_settings", column)
