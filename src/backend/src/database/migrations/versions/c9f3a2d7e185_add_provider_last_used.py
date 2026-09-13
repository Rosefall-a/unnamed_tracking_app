"""add provider_last_used to user_scan_settings

Revision ID: c9f3a2d7e185
Revises: b2e7c4a91f56
Create Date: 2026-09-05

Tracks, per user, the last epoch second each metadata provider actually
returned a result during a search — shown in Scan Settings so it's obvious
which providers are stale/unused instead of a bare on/off toggle with no
history.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c9f3a2d7e185"
down_revision: Union[str, None] = "b2e7c4a91f56"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_scan_settings",
        sa.Column("provider_last_used", sa.JSON(), nullable=False, server_default="{}"),
    )


def downgrade() -> None:
    op.drop_column("user_scan_settings", "provider_last_used")
