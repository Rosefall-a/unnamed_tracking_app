"""add provider credentials to users

Revision ID: b4e91c2a7f08
Revises: 9d2a7e5f6b13
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b4e91c2a7f08"
down_revision: Union[str, None] = "9d2a7e5f6b13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("retroachievements_api_key", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("giantbomb_api_key", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("screenscraper_ssid", sa.String(length=64), nullable=True))
    op.add_column("users", sa.Column("screenscraper_sspassword", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("xbox_client_id", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("xbox_client_secret", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("gog_refresh_token", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "gog_refresh_token")
    op.drop_column("users", "xbox_client_secret")
    op.drop_column("users", "xbox_client_id")
    op.drop_column("users", "screenscraper_sspassword")
    op.drop_column("users", "screenscraper_ssid")
    op.drop_column("users", "giantbomb_api_key")
    op.drop_column("users", "retroachievements_api_key")
