"""add soft-delete to media_items

Revision ID: f2c8a5e3b719
Revises: e7b3f9a1c4d6
Create Date: 2026-09-05

Deleting an assigned screenshot/clip/soundtrack previously unlinked the
file and removed the row immediately, same instant-and-permanent pattern
as the game archives incident this whole trash system exists to fix.
Same approach here: deleted_at marks it trashed, the file moves to
_trash alongside it, and features/trash/sweep.py purges both after 7
days.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2c8a5e3b719"
down_revision: Union[str, None] = "e7b3f9a1c4d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("media_items", sa.Column("deleted_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("media_items", "deleted_at")
