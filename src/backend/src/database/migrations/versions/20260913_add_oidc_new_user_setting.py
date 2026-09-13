"""add OIDC new-user creation setting

Revision ID: 20260913_add_oidc_new_user_setting
Revises: 20260913_add_oidc_login_ui
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_add_oidc_new_users"
down_revision: Union[str, None] = "20260913_add_oidc_login_ui"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oidc_settings",
        sa.Column("allow_new_users", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("oidc_settings", "allow_new_users")
