"""let lists be pinned and put in the user's own order

Both columns are added only if missing, so this is safe on a database that
already has them (see docs/migrations.md).

Revision ID: d3f7a1c5b9e2
Revises: c9a2e6b4d8f1
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d3f7a1c5b9e2"
down_revision: Union[str, None] = "c9a2e6b4d8f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE media_lists ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT false")
    op.execute("ALTER TABLE media_lists ADD COLUMN IF NOT EXISTS position INTEGER NOT NULL DEFAULT 0")


def downgrade() -> None:
    op.execute("ALTER TABLE media_lists DROP COLUMN IF EXISTS position")
    op.execute("ALTER TABLE media_lists DROP COLUMN IF EXISTS pinned")
