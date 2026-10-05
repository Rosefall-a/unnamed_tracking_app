"""Record which achievements a provider marks as hidden.

Steam and PlayStation both flag hidden achievements in what they send; the
sync read the flag and dropped it, so a hidden achievement showed up like any
other. It is a spoiler until unlocked, so the page needs it.

Create-if-missing, so this is safe on a database adopted from an older
history (see src/database/migrate.py). Existing rows start as not hidden and
are filled in the next time each game syncs.

revision: c4d8e2f6a1b7
down_revision: a3f1c7e9d2b4
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "c4d8e2f6a1b7"
down_revision: str | None = "a3f1c7e9d2b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing(
        "achievements",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )


def downgrade() -> None:
    op.execute("ALTER TABLE achievements DROP COLUMN IF EXISTS hidden")
