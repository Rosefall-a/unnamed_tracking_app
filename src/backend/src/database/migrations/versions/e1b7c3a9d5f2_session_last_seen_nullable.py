"""Let user_sessions.last_seen_at be NULL again.

Databases that already ran the removed session-metadata migration have the
column set NOT NULL, and the current code never writes it, so every login
would fail on insert. A database without the column is left alone.

revision: e1b7c3a9d5f2
down_revision: c4f1d2e8a9b0
"""

from collections.abc import Sequence

from alembic import op

from src.database import migration_helpers as h

revision: str = "e1b7c3a9d5f2"
down_revision: str | None = "c4f1d2e8a9b0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if h.has_column("user_sessions", "last_seen_at"):
        op.alter_column("user_sessions", "last_seen_at", nullable=True)


def downgrade() -> None:
    pass
