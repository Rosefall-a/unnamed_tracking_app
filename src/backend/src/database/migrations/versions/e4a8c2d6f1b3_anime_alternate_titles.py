"""keep an anime's English, romaji and Japanese titles

Added only if missing, so it is safe on a database that already has them
(see docs/migrations.md).

Revision ID: e4a8c2d6f1b3
Revises: d3f7a1c5b9e2
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "e4a8c2d6f1b3"
down_revision: Union[str, None] = "d3f7a1c5b9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ("title_english", "title_romaji", "title_native")


def upgrade() -> None:
    for column in _COLUMNS:
        op.execute(f"ALTER TABLE anime ADD COLUMN IF NOT EXISTS {column} VARCHAR(500)")


def downgrade() -> None:
    for column in reversed(_COLUMNS):
        op.execute(f"ALTER TABLE anime DROP COLUMN IF EXISTS {column}")
