"""add image save toggles to scan settings

Revision ID: a1d4f6c8b3e0
Revises: c7f0a3e5d9b2
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1d4f6c8b3e0"
down_revision: Union[str, None] = "c7f0a3e5d9b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for column in ("save_key_art", "save_banner", "save_logo", "save_icon"):
        op.add_column(
            "user_scan_settings",
            sa.Column(column, sa.Boolean(), nullable=False, server_default=sa.true()),
        )


def downgrade() -> None:
    for column in ("save_icon", "save_logo", "save_banner", "save_key_art"):
        op.drop_column("user_scan_settings", column)
