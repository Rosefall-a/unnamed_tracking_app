"""Give media a title and a real "taken" date.

media_items gains a title (an in-app name, the file keeps its own) and
taken_at / taken_source (when it was captured and where that date came from).
inbox_items gains taken_at / taken_source so the date survives being assigned
to a game. Existing rows stay NULL and keep showing their upload date.

Create-if-missing, so this is safe on a database adopted from an older history
(see src/database/migrate.py).

revision: e2a7c9b4d1f6
down_revision: d9e1f3a5b7c2
"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.database import migration_helpers as h

revision: str = "e2a7c9b4d1f6"
down_revision: str | None = "d9e1f3a5b7c2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("media_items", sa.Column("title", sa.String(200), nullable=True))
    h.add_column_if_missing("media_items", sa.Column("taken_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing("media_items", sa.Column("taken_source", sa.String(20), nullable=True))
    h.add_column_if_missing("inbox_items", sa.Column("taken_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing("inbox_items", sa.Column("taken_source", sa.String(20), nullable=True))


def downgrade() -> None:
    pass
