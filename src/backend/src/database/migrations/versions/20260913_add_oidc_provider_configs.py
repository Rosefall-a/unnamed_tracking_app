"""add multiple OIDC provider configurations

Revision ID: 20260913_oidc_providers
Revises: 20260913_add_oidc_new_users, 7a2c1b9e4d10, c3e7f1a9b2d4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_oidc_providers"
down_revision: Union[str, Sequence[str], None] = (
    "20260913_add_oidc_new_users",
    "7a2c1b9e4d10",
    "c3e7f1a9b2d4",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("oidc_settings", sa.Column("providers_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("oidc_settings", "providers_json")
