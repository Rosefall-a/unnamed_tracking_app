"""add OIDC group mapping settings

Revision ID: 20260913_add_oidc_group_settings
Revises: 20260911_merge_api_key_heads
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_add_oidc_group_settings"
down_revision: Union[str, None] = "20260911_merge_api_key_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "oidc_settings",
        sa.Column("groups_claim", sa.String(length=128), nullable=False, server_default="groups"),
    )
    op.add_column(
        "oidc_settings",
        sa.Column("admin_group", sa.String(length=256), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("oidc_settings", "admin_group")
    op.drop_column("oidc_settings", "groups_claim")
