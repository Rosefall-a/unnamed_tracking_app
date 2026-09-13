"""add deployment-wide OIDC settings

Revision ID: b8d2e6f4c1a9
Revises: 20260911_merge_api_key_heads
Create Date: 2026-09-13

OIDC is configured from the admin Settings page. The client secret is stored
encrypted at rest; only the issuer/client ID are returned to the frontend.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b8d2e6f4c1a9"
down_revision: Union[str, None] = "20260911_merge_api_key_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("app_integration_settings", sa.Column("oidc_issuer_url", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("oidc_client_id", sa.String(length=256), nullable=True))
    op.add_column("app_integration_settings", sa.Column("oidc_client_secret", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("oidc_scopes", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("oidc_redirect_uri", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_integration_settings", "oidc_redirect_uri")
    op.drop_column("app_integration_settings", "oidc_scopes")
    op.drop_column("app_integration_settings", "oidc_client_secret")
    op.drop_column("app_integration_settings", "oidc_client_id")
    op.drop_column("app_integration_settings", "oidc_issuer_url")
