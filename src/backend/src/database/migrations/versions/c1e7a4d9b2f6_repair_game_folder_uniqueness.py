"""repair game folder uniqueness after the per-user migration

Revision ID: c1e7a4d9b2f6
Revises: b7c4e2f1a935
Create Date: 2026-09-11

Some existing databases can have b7c4e2f1a935 recorded as applied while
still retaining the old server-wide folder index.  That leaves the API
checking the correct per-user scope in application code while PostgreSQL
still rejects a valid folder used by another user.

This migration is intentionally idempotent so it repairs either schema
state without requiring manual database changes.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c1e7a4d9b2f6"
down_revision: Union[str, None] = "b7c4e2f1a935"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # b7c4e2f1a935 replaces this index, but a database that was stamped or
    # otherwise left with that revision can still have the old index around.
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
    # The repaired schema is identical to b7c4e2f1a935's intended upgrade
    # state, so reverting this repair must leave that revision's schema in
    # place for Alembic to downgrade next.
    pass
