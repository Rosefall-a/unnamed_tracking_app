"""repair game folder uniqueness after the per-user migration

Revision ID: c1e7a4d9b2f6
Revises: b7e4c2f9a1d6
Create Date: 2026-09-11

Some existing databases can have the per-user folder migration recorded as
applied while still retaining the old server-wide folder index. This repair
removes that stale database object and restores the intended per-user
constraint without creating a second Alembic head.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1e7a4d9b2f6"
down_revision: Union[str, None] = "b7e4c2f9a1d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # The Playnite GUID migration is the other child of the per-user folder
    # migration. Making this repair depend on it keeps the migration graph
    # linear and lets Alembic's normal `upgrade head` command work.
    op.execute(sa.text("DROP INDEX IF EXISTS ix_games_folder_location_active"))
    op.execute(sa.text("ALTER TABLE games DROP CONSTRAINT IF EXISTS games_folder_location_key"))
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ix_games_user_folder_location_active
            ON games (user_id, folder_location)
            WHERE deleted_at IS NULL
            """
        )
    )


def downgrade() -> None:
    # The previous migration owns the intended per-user index, so there is
    # nothing to undo here. Alembic will move back to b7e4c2f9a1d6.
    pass
