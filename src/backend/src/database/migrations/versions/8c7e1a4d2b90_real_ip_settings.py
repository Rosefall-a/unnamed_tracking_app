"""Add production Nginx real-IP deployment settings."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "8c7e1a4d2b90"
down_revision: str | None = "7b2d4a9e8c11"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column("nginx_realip_header", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("nginx_realip_trusted_proxies", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "nginx_realip_trusted_proxies")
    op.drop_column("app_integration_settings", "nginx_realip_header")
