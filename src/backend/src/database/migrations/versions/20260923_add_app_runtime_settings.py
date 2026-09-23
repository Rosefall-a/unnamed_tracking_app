"""persist application runtime settings

Revision ID: 20260923_app_runtime
Revises: f186cf8aa5c4
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260923_app_runtime"
down_revision: Union[str, None] = "f186cf8aa5c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column("auth_cookie_secure", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("max_upload_size_mb", sa.Integer(), nullable=False, server_default="15"),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("max_clip_size_mb", sa.Integer(), nullable=False, server_default="500"),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("max_world_save_size_mb", sa.Integer(), nullable=False, server_default="2000"),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("runtime_settings_initialized", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    for column in (
        "runtime_settings_initialized",
        "max_world_save_size_mb",
        "max_clip_size_mb",
        "max_upload_size_mb",
        "auth_cookie_secure",
    ):
        op.drop_column("app_integration_settings", column)
