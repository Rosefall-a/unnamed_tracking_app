"""Add manual metadata locks to games.

revision: c4f1d2e8a9b0
down_revision: 7b2d4a9e8c11
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "c4f1d2e8a9b0"
down_revision: str | None = "a3f1c7e9d2b4"
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
