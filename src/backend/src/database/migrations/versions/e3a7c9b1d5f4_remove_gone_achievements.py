"""A setting for whether a sync removes achievements a game no longer has.

On by default, so an achievement the developer took out goes from the list.
Turned off, every achievement ever seen is kept, unlocked or not.

Revision ID: e3a7c9b1d5f4
Revises: d8f2b6a4e1c3
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "e3a7c9b1d5f4"
down_revision: str | None = "d8f2b6a4e1c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing(
        "user_scan_settings",
        sa.Column(
            "remove_gone_achievements",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_scan_settings", "remove_gone_achievements")
