"""add password reset setting

Revision ID: 20260913_reset_flag
Revises: 20260913_smtp_reset

The initial schema already contains password_reset_enabled, so this historical
revision is retained as a no-op rather than attempting to add the column again.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260913_reset_flag"
down_revision: Union[str, None] = "20260913_smtp_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
