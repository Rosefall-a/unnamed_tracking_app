"""persist admin-configurable runtime settings

Revision ID: 20260914_app_runtime
Revises: 20260913_smtp_reset

The initial schema already contains the four core runtime settings columns.
Only runtime_settings_initialized is introduced by this revision.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_app_runtime"
down_revision: Union[str, None] = "20260913_smtp_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column(
            "runtime_settings_initialized", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "runtime_settings_initialized")
