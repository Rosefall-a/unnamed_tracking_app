"""Add manual metadata locks to games.

revision: c4f1d2e8a9b0
down_revision: 8c7e1a4d2b90
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "c4f1d2e8a9b0"
down_revision: str | None = "8c7e1a4d2b90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing(
        "games",
        sa.Column(
            "locked_fields",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
    )
    op.alter_column("games", "locked_fields", server_default=None)


def downgrade() -> None:
    op.drop_column("games", "locked_fields")
