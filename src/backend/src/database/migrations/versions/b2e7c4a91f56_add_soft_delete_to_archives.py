"""add soft-delete to game archives and versions

Revision ID: b2e7c4a91f56
Revises: f4c1a8e6d2b9
Create Date: 2026-09-05

A hard-delete of an archive or version previously ran shutil.rmtree
immediately with no recovery window — a scripting mistake or a misclick
meant real, irreplaceable save data was just gone. deleted_at marks an
archive/version as trashed instead of removing it; a background sweep
(see features/trash/sweep.py) permanently purges anything trashed for
more than 7 days, and only the sweep ever calls rmtree.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2e7c4a91f56"
down_revision: Union[str, None] = "f4c1a8e6d2b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("game_archives", sa.Column("deleted_at", sa.BigInteger(), nullable=True))
    op.add_column("game_archive_versions", sa.Column("deleted_at", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("game_archive_versions", "deleted_at")
    op.drop_column("game_archives", "deleted_at")
