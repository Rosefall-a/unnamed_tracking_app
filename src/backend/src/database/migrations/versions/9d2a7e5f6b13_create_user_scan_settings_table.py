"""create user scan settings table

Revision ID: 9d2a7e5f6b13
Revises: 3b6d8f0a1c4e
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9d2a7e5f6b13"
down_revision: Union[str, None] = "3b6d8f0a1c4e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_scan_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column(
            "provider_order",
            sa.JSON(),
            nullable=False,
            server_default='["Steam", "SteamGridDB"]',
        ),
        sa.Column("save_developer", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_publisher", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_series", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_tags", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_features", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_description", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_age_rating", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("save_release_date", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_scan_settings")
