"""Record how many players have each achievement.

Steam publishes a global percentage per achievement, PlayStation sends each
trophy's earned rate, and RetroAchievements says how many players earned it.
The page shows it as "of players"; this is where it is kept.

Create-if-missing, so this is safe on a database adopted from an older
history (see src/database/migrate.py). Existing rows have no percentage until
their achievements are refreshed.

revision: d9e1f3a5b7c2
down_revision: c4d8e2f6a1b7
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "d9e1f3a5b7c2"
down_revision: str | None = "c4d8e2f6a1b7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing("achievements", sa.Column("global_percent", sa.Float(), nullable=True))


def downgrade() -> None:
    op.execute("ALTER TABLE achievements DROP COLUMN IF EXISTS global_percent")
