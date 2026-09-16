"""add is_airing to anime and tv_shows

Revision ID: b7e4d2a9c168
Revises: a2f6c8d1e953
Create Date: 2026-09-15

Lets the frequent airing-check loop filter down to just shows that are
actually still airing, instead of re-checking every already-synced show
on every cycle. NULL means "not checked yet" (falls into the check until
it's actually determined either way).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7e4d2a9c168"
down_revision: Union[str, None] = "a2f6c8d1e953"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anime", sa.Column("is_airing", sa.Boolean(), nullable=True))
    op.add_column("tv_shows", sa.Column("is_airing", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("tv_shows", "is_airing")
    op.drop_column("anime", "is_airing")
