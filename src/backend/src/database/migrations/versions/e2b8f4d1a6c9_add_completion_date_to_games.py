"""add completion_date to games

Revision ID: e2b8f4d1a6c9
Revises: d9a1e5c3f7b8
Create Date: 2026-09-08

Tracks when a game was first 100%-completed (Mastered) — set automatically
the first time a game's status transitions to Mastered, editable
afterward like purchase_date.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e2b8f4d1a6c9"
down_revision: Union[str, None] = "d9a1e5c3f7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("completion_date", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "completion_date")
