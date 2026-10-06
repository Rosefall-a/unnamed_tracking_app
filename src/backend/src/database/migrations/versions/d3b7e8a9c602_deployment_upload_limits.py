"""deployment upload limits

Revision ID: d3b7e8a9c602
Revises: c2a9e6f4b801
Create Date: 2026-10-04 18:23:00.964320

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

# revision identifiers, used by Alembic.
revision: str = "d3b7e8a9c602"
down_revision: Union[str, None] = "c2a9e6f4b801"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Preserve existing values; null means use the environment default."""
    h.add_column_if_missing(
        "app_integration_settings",
        sa.Column("max_save_archive_size_mb", sa.Integer(), nullable=True),
    )
    h.add_column_if_missing(
        "app_integration_settings", sa.Column("max_clip_size_mb", sa.Integer(), nullable=True)
    )
    h.add_column_if_missing(
        "app_integration_settings", sa.Column("max_world_save_size_mb", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    """Remove only the new overrides; keep branding and integrations."""
    op.execute("ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS max_world_save_size_mb")
    op.execute("ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS max_clip_size_mb")
    op.execute("ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS max_save_archive_size_mb")
