"""Add production Nginx real-IP deployment settings."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from src.database import migration_helpers as h

revision: str = "8c7e1a4d2b90"
down_revision: str | None = "d4a8b2c6e9f1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    h.add_column_if_missing(
        "app_integration_settings",
        sa.Column("nginx_realip_header", sa.String(length=128), nullable=True),
    )
    h.add_column_if_missing(
        "app_integration_settings",
        sa.Column("nginx_realip_trusted_proxies", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS nginx_realip_trusted_proxies"
    )
    op.execute("ALTER TABLE app_integration_settings DROP COLUMN IF EXISTS nginx_realip_header")
