"""add separate image provider order to scan settings

Revision ID: d5e2a9c1f4b6
Revises: a1d4f6c8b3e0
Create Date: 2026-09-04

"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d5e2a9c1f4b6"
down_revision: Union[str, None] = "a1d4f6c8b3e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DEFAULT_ORDER = ["Steam", "IGDB", "GiantBomb", "RetroAchievements", "SteamGridDB", "ScreenScraper", "HowLongToBeat"]


def upgrade() -> None:
    op.add_column(
        "user_scan_settings",
        sa.Column(
            "image_provider_order",
            sa.JSON(),
            nullable=False,
            server_default=json.dumps(_DEFAULT_ORDER),
        ),
    )


def downgrade() -> None:
    op.drop_column("user_scan_settings", "image_provider_order")
