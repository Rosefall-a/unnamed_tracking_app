"""Save a preview picture and the length of each clip.

media_items gains thumb_filename and duration, so the clips gallery can show a
stored picture and length instead of loading every video to find them.

Create-if-missing, so this is safe on a database adopted from an older history
(see src/database/migrate.py).

revision: c7e1f5a9d3b2
down_revision: b6d9e2f4a8c1
"""

from collections.abc import Sequence

import sqlalchemy as sa

from src.database import migration_helpers as h

revision: str = "c7e1f5a9d3b2"
down_revision: str | None = "b6d9e2f4a8c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("media_items", sa.Column("thumb_filename", sa.String(300), nullable=True))
    h.add_column_if_missing("media_items", sa.Column("duration", sa.Float(), nullable=True))


def downgrade() -> None:
    pass
