"""add last_played_at to games

Revision ID: a3d7f1c9e5b2
Revises: f7c2a4e8b1d9
Create Date: 2026-09-06

Populated from Steam's rtime_last_played during a library sync (the
"Recent Activity" field was previously always blank — it read from
frontend-only mock platform data that no real sync ever populated).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a3d7f1c9e5b2"
down_revision: Union[str, None] = "f7c2a4e8b1d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("last_played_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("games", "last_played_at")
