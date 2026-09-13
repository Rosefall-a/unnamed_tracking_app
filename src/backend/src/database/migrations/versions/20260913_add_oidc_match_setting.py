"""add OIDC user matching setting

Revision ID: 20260913_add_oidc_match_setting
Revises: 20260913_add_oidc_group_settings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_add_oidc_match_setting"
down_revision: Union[str, None] = "20260913_add_oidc_group_settings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oidc_settings",
        sa.Column("user_match_field", sa.String(length=16), nullable=False, server_default="email"),
    )


def downgrade() -> None:
    op.drop_column("oidc_settings", "user_match_field")
