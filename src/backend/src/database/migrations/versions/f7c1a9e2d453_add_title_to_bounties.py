"""add title to bounties

Revision ID: f7c1a9e2d453
Revises: e6a2f7c1d834
Create Date: 2026-09-06

Bounties are now user-authored goals inside a game ("reach level 50",
"beat the final boss") rather than system-picked idle nudges — the old
auto-picked rows don't fit that shape, so they're cleared rather than
backfilled with a placeholder title.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f7c1a9e2d453"
down_revision: Union[str, None] = "e6a2f7c1d834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DELETE FROM bounties")
    op.add_column("bounties", sa.Column("title", sa.String(length=200), nullable=False))
    op.add_column("bounties", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("bounties", "notes")
    op.drop_column("bounties", "title")
