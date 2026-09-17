"""add kitsu_id to anime

Revision ID: c4f8a2e6b9d1
Revises: b6e1a3f9c7d2
Create Date: 2026-09-16

Adds `anime.kitsu_id` — Kitsu is a third, keyless episode-data source
(real per-episode thumbnails, which Jikan's API has none of at all)
alongside AniList and MyAnimeList. Stored once an exact-title match is
found so episode sync doesn't repeat that search on every fetch.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c4f8a2e6b9d1"
down_revision: Union[str, None] = "b6e1a3f9c7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anime", sa.Column("kitsu_id", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("anime", "kitsu_id")
