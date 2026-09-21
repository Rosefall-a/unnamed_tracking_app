"""add deployment-wide provider credentials

Revision ID: a6c1e9f4b2d7
Revises: a5f8c3e1b746
Create Date: 2026-09-11

Extend the existing deployment-wide integration settings row so all
shareable provider credentials can be managed from the database instead of
being limited to IGDB. User credentials still take precedence.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a6c1e9f4b2d7"
down_revision: Union[str, None] = "a5f8c3e1b746"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column("steamgriddb_api_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("retroachievements_api_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("giantbomb_api_key", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("screenscraper_ssid", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("screenscraper_sspassword", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("screenscraper_devid", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("screenscraper_devpassword", sa.Text(), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("xbox_client_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "app_integration_settings",
        sa.Column("xbox_client_secret", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "xbox_client_secret")
    op.drop_column("app_integration_settings", "xbox_client_id")
    op.drop_column("app_integration_settings", "screenscraper_devpassword")
    op.drop_column("app_integration_settings", "screenscraper_devid")
    op.drop_column("app_integration_settings", "screenscraper_sspassword")
    op.drop_column("app_integration_settings", "screenscraper_ssid")
    op.drop_column("app_integration_settings", "giantbomb_api_key")
    op.drop_column("app_integration_settings", "retroachievements_api_key")
    op.drop_column("app_integration_settings", "steamgriddb_api_key")
