"""Give saves and worlds a note and tags.

game_archives gains a note and tags, so a save or world can be described and
sorted like a doc or a screenshot.

Create-if-missing, so this is safe on a database adopted from an older history
(see src/database/migrate.py).

revision: d4a8b2c6e9f1
down_revision: c7e1f5a9d3b2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "d4a8b2c6e9f1"
down_revision: str | None = "c7e1f5a9d3b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("game_archives", sa.Column("note", sa.Text(), nullable=True))
    h.add_column_if_missing(
        "game_archives",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )


def downgrade() -> None:
    pass
