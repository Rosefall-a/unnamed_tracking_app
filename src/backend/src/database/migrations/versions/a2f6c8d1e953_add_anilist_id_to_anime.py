"""add anilist_id to anime

Revision ID: a2f6c8d1e953
Revises: e7b3c1a9f450
Create Date: 2026-09-15

Episode sync only ever tried Jikan/MyAnimeList (via `external_id`), which
turns out to be unreliable (rate limits, occasional outages) with no
fallback — this adds a second id, AniList's own, so episode sync can fall
back to AniList's streamingEpisodes data when Jikan fails or was never
matched for a given entry.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a2f6c8d1e953"
down_revision: Union[str, None] = "e7b3c1a9f450"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anime", sa.Column("anilist_id", sa.String(length=50), nullable=True))


def downgrade() -> None:
    op.drop_column("anime", "anilist_id")
