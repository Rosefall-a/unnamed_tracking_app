"""add real library-sync timestamps to users

Revision ID: c6a8f2e4b9d3
Revises: b3d9e5c7a2f1
Create Date: 2026-09-04

Previously "last synced" was derived from MAX(games.updated_at) for a given
source — misleading, since that's also touched by unrelated metadata-search
edits on games that were never actually pulled in by a library sync. These
columns are set explicitly by library_sync.py on a successful run instead.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6a8f2e4b9d3"
down_revision: Union[str, None] = "b3d9e5c7a2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("steam_library_synced_at", sa.BigInteger(), nullable=True))
    op.add_column(
        "users", sa.Column("retroachievements_library_synced_at", sa.BigInteger(), nullable=True)
    )
    op.add_column("users", sa.Column("psn_library_synced_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "psn_library_synced_at")
    op.drop_column("users", "retroachievements_library_synced_at")
    op.drop_column("users", "steam_library_synced_at")
