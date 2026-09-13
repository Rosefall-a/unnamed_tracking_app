"""add multiple OIDC provider configurations

Revision ID: 20260913_add_oidc_provider_configs
Revises: 20260913_add_oidc_new_users
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "20260913_add_oidc_provider_configs"
down_revision: Union[str, None] = "20260913_add_oidc_new_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("oidc_settings", sa.Column("providers_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("oidc_settings", "providers_json")
