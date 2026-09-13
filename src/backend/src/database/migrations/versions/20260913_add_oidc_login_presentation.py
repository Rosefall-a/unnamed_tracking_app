"""add OIDC login presentation settings

Revision ID: 20260913_add_oidc_login_presentation
Revises: 20260913_add_oidc_user_match
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_add_oidc_login_presentation"
down_revision: Union[str, None] = "20260913_add_oidc_user_match"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oidc_settings",
        sa.Column(
            "default_login_method", sa.String(length=16), nullable=False, server_default="local"
        ),
    )
    op.add_column(
        "oidc_settings",
        sa.Column(
            "login_button_text",
            sa.String(length=100),
            nullable=False,
            server_default="Continue with SSO",
        ),
    )


def downgrade() -> None:
    op.drop_column("oidc_settings", "login_button_text")
    op.drop_column("oidc_settings", "default_login_method")
