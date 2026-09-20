"""persist admin-configurable runtime settings

Revision ID: 20260914_app_runtime
Revises: 20260913_smtp_reset

All columns introduced by this historical migration are already present in
the initial schema. Keep the revision as a no-op so the migration history
remains traversable without recreating existing columns.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260914_app_runtime"
down_revision: Union[str, None] = "20260913_smtp_reset"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
