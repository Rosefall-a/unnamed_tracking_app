"""Reconcile session network ownership metadata from the maintenance branch.

Migration repair: main's e7f1a2b3c4d5 now owns these columns too. Retain this
revision for databases that already applied it, and guard additions for either
predecessor schema. Downgrades retain columns owned by the predecessor.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.database import migration_helpers as h

revision: str = "f2a8c9d0e1b2"
down_revision: str = "e7f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing(
        "user_sessions", sa.Column("geo_network_number", sa.BigInteger(), nullable=True)
    )
    h.add_column_if_missing(
        "user_sessions",
        sa.Column("geo_network_organization", sa.String(256), nullable=True),
    )


def downgrade() -> None:
    """Keep the network columns required by e7f1a2b3c4d5."""
