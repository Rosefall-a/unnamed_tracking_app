"""add time to beat to games and its scan settings toggle

Revision ID: c7f0a3e5d9b2
Revises: b4e91c2a7f08
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c7f0a3e5d9b2"
down_revision: Union[str, None] = "b4e91c2a7f08"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("time_to_beat_hours", sa.Numeric(6, 1), nullable=True))
    op.add_column(
        "user_scan_settings",
        sa.Column("save_time_to_beat", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("user_scan_settings", "save_time_to_beat")
    op.drop_column("games", "time_to_beat_hours")
