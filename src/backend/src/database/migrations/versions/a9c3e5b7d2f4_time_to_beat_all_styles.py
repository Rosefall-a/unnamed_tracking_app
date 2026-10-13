"""Every HowLongToBeat time on a game, not only the main story.

Revision ID: a9c3e5b7d2f4
Revises: e7b3c9d1a5f2
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "a9c3e5b7d2f4"
down_revision: str | None = "e7b3c9d1a5f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_COLUMNS = (
    "time_to_beat_extras_hours",
    "time_to_beat_completionist_hours",
    "time_to_beat_all_hours",
)


def upgrade() -> None:
    for name in _COLUMNS:
        h.add_column_if_missing("games", sa.Column(name, sa.Numeric(6, 1), nullable=True))


def downgrade() -> None:
    for name in reversed(_COLUMNS):
        op.drop_column("games", name)
