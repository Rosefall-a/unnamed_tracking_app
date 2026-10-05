"""Give doc and modpack files the same details as media.

game_file_items gains a title, a note, tags and a taken date (with where the
date came from), so Docs works like the Screenshots gallery.

Create-if-missing, so this is safe on a database adopted from an older history
(see src/database/migrate.py).

revision: f3b8d5a1c7e2
down_revision: e2a7c9b4d1f6
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "f3b8d5a1c7e2"
down_revision: str | None = "e2a7c9b4d1f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("game_file_items", sa.Column("title", sa.String(200), nullable=True))
    h.add_column_if_missing("game_file_items", sa.Column("note", sa.Text(), nullable=True))
    h.add_column_if_missing(
        "game_file_items",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    h.add_column_if_missing("game_file_items", sa.Column("taken_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing(
        "game_file_items", sa.Column("taken_source", sa.String(20), nullable=True)
    )


def downgrade() -> None:
    pass
