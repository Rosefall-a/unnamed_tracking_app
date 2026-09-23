"""add deployment SMTP settings

Revision ID: 20260923_add_deployment_smtp_settings
Revises: 20260913_oidc_providers
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_add_deployment_smtp_settings"
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
    op.add_column("app_integration_settings", sa.Column("password_reset_enabled", sa.Boolean(), nullable=False, server_default=sa.true()))


def downgrade() -> None:
    op.drop_column("app_integration_settings", "password_reset_enabled")
    op.drop_column("app_integration_settings", "smtp_from_name")
    op.drop_column("app_integration_settings", "smtp_from_email")
    op.drop_column("app_integration_settings", "smtp_use_ssl")
    op.drop_column("app_integration_settings", "smtp_use_tls")
    op.drop_column("app_integration_settings", "smtp_password")
    op.drop_column("app_integration_settings", "smtp_username")
    op.drop_column("app_integration_settings", "smtp_port")
    op.drop_column("app_integration_settings", "smtp_host")
    op.drop_column("app_integration_settings", "smtp_enabled")
