"""add soft-delete to games

Revision ID: e7b3f9a1c4d6
Revises: d4a6e9c2f731
Create Date: 2026-09-05

Deleting a game previously removed the row (and cascaded to its
screenshots/clips/achievements/notes/everything) instantly and
permanently, with a plain "this can't be undone" warning as the only
safety net -- the highest-blast-radius delete in the app had the weakest
protection. deleted_at follows the same pattern as GameArchive: NULL
means active, set means trashed, and features/trash/sweep.py purges the
row and moves the game's on-disk folder to trash for good after 7 days.

folder_location's plain unique constraint would otherwise block reusing
a deleted game's folder name for the whole trash window, so it's
replaced with a partial unique index that only applies to active
(non-deleted) games.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3f9a1c4d6"
down_revision: Union[str, None] = "d4a6e9c2f731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("games", sa.Column("deleted_at", sa.BigInteger(), nullable=True))
    op.drop_constraint("games_folder_location_key", "games", type_="unique")
    op.create_index(
        "ix_games_folder_location_active",
        "games",
        ["folder_location"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_games_folder_location_active", table_name="games")
    op.create_unique_constraint("games_folder_location_key", "games", ["folder_location"])
    op.drop_column("games", "deleted_at")
