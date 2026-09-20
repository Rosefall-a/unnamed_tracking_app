"""add deployment-wide provider credentials

Revision ID: a6c1e9f4b2d7
Revises: f6bb4f914739
Create Date: 2026-09-11

The initial schema already contains the deployment-wide provider credential
columns. This revision is retained as a historical graph node but performs no
schema changes so existing databases can traverse the corrected history
without attempting to recreate columns that already exist.
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
