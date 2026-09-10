"""strictly separate data vs image provider order lists

Revision ID: e7f3b2a1c9d4
Revises: d5e2a9c1f4b6
Create Date: 2026-09-04

Existing rows were written back when both `provider_order` and
`image_provider_order` shared the same 7-provider set. This filters each
column down to its own content-scoped set (search.py's DATA_PROVIDER_NAMES /
IMAGE_PROVIDER_NAMES) so the Settings UI doesn't show stale, no-op entries
(e.g. SteamGridDB inside "Data provider order").
"""

import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7f3b2a1c9d4"
down_revision: Union[str, None] = "d5e2a9c1f4b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_DATA_PROVIDERS = {"Steam", "IGDB", "GiantBomb", "RetroAchievements", "HowLongToBeat"}
_IMAGE_PROVIDERS = {"SteamGridDB", "ScreenScraper"}
_DEFAULT_DATA_ORDER = ["Steam", "IGDB", "GiantBomb", "RetroAchievements", "HowLongToBeat"]
_DEFAULT_IMAGE_ORDER = ["SteamGridDB", "ScreenScraper"]


def upgrade() -> None:
    op.alter_column(
        "user_scan_settings",
        "image_provider_order",
        server_default=json.dumps(_DEFAULT_IMAGE_ORDER),
    )

    connection = op.get_bind()
    rows = connection.execute(
        sa.text("SELECT id, provider_order, image_provider_order FROM user_scan_settings")
    ).fetchall()
    for row_id, provider_order, image_provider_order in rows:
        filtered_data = [
            p for p in (provider_order or []) if p in _DATA_PROVIDERS
        ] or _DEFAULT_DATA_ORDER
        filtered_image = [
            p for p in (image_provider_order or []) if p in _IMAGE_PROVIDERS
        ] or _DEFAULT_IMAGE_ORDER
        connection.execute(
            sa.text(
                "UPDATE user_scan_settings SET provider_order = :data, image_provider_order = :image WHERE id = :id"
            ),
            {"data": json.dumps(filtered_data), "image": json.dumps(filtered_image), "id": row_id},
        )


def downgrade() -> None:
    op.alter_column("user_scan_settings", "image_provider_order", server_default=None)
