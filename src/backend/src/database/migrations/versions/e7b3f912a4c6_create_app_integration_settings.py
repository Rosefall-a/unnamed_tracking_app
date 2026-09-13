"""create app_integration_settings

Revision ID: e7b3f912a4c6
Revises: d4a7c2e9f138
Create Date: 2026-09-06

A deployment-wide singleton row for API credentials that belong to the
server itself, not to any one user (an IGDB/Twitch developer app is
registered once per self-hosted instance, admin-entered through Settings —
never baked into .env, so a downloaded copy of this app never ships with
someone else's credentials).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e7b3f912a4c6"
down_revision: Union[str, None] = "d4a7c2e9f138"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_integration_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("igdb_client_id", sa.String(length=128), nullable=True),
        sa.Column("igdb_client_secret", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("app_integration_settings")
