"""add deployment-wide provider credentials

Revision ID: a6c1e9f4b2d7
Revises: f6bb4f914739

The initial schema already contains these deployment-wide credential columns.
This revision is retained as a historical graph node but performs no schema
changes.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a6c1e9f4b2d7"
down_revision: Union[str, None] = "f6bb4f914739"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
