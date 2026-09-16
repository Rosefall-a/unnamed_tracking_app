"""add password reset setting

Revision ID: 20260913_reset_flag
Revises: 20260913_smtp_reset
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_reset_flag"
down_revision: Union[str, None] = "20260913_smtp_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column("password_reset_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "password_reset_enabled")
