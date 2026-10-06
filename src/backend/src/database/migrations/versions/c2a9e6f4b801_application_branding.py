"""Persist deployment branding independently of personal appearance.

Revision ID: c2a9e6f4b801
Revises: b8c7d6e5f403
"""

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision = "c2a9e6f4b801"
down_revision = "b8c7d6e5f403"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Extend the existing deployment singleton; preserve configured providers."""
    h.add_column_if_missing(
        "app_integration_settings", sa.Column("branding_name", sa.String(64), nullable=True)
    )
    for name in ("branding_logo_png", "branding_favicon_png"):
        h.add_column_if_missing(
            "app_integration_settings", sa.Column(name, sa.LargeBinary(), nullable=True)
        )


def downgrade() -> None:
    """Remove branding without affecting provider credentials or user preferences."""
    for name in ("branding_name", "branding_logo_png", "branding_favicon_png"):
        op.execute(f"ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS {name}")
