"""add games.osrs_stats_enabled

Revision ID: d5f8a1c3b924
Revises: c8d4b6e9a271
Create Date: 2026-09-06

A second, independent per-game toggle alongside profiles_enabled — the
generic accounts/checklist/media-grouping feature works for any game, but
the WiseOldMan sync/icons/skill-boss grouping on the Stats card is
OSRS-specific and shouldn't show up for every other game's accounts.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5f8a1c3b924"
down_revision: Union[str, None] = "c8d4b6e9a271"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("osrs_stats_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("games", "osrs_stats_enabled")
