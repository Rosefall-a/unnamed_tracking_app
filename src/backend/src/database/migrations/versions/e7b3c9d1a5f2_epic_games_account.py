"""Add the Epic Games account connection to users.

revision: e7b3c9d1a5f2
down_revision: c4f1d2e8a9b0
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "e7b3c9d1a5f2"
down_revision: str | None = "c4f1d2e8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("users", sa.Column("epic_refresh_token", sa.Text(), nullable=True))
    h.add_column_if_missing("users", sa.Column("epic_account_id", sa.String(64), nullable=True))
    h.add_column_if_missing("users", sa.Column("epic_display_name", sa.String(128), nullable=True))
    h.add_column_if_missing(
        "users", sa.Column("epic_library_synced_at", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    for column in (
        "epic_library_synced_at",
        "epic_display_name",
        "epic_account_id",
        "epic_refresh_token",
    ):
        op.drop_column("users", column)
