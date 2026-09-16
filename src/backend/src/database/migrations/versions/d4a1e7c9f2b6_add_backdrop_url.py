"""add backdrop_url to movies/tv_shows/anime

Revision ID: d4a1e7c9f2b6
Revises: c9f2a6e1d834
Create Date: 2026-09-14

Adds a `backdrop_url` column alongside each entity's existing `poster_url`
— a wide-format background image (TMDB's `backdrop_path`, AniList's
`bannerImage`) distinct from the portrait poster, so the detail page hero
can show a real background instead of a blurred poster. Same convention
as `poster_url`: a direct external CDN URL, never downloaded/resized.
Nullable everywhere since not every provider returns one (TVmaze, Jikan,
OMDb have no separate backdrop/banner field).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a1e7c9f2b6"
down_revision: Union[str, None] = "c9f2a6e1d834"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("backdrop_url", sa.Text(), nullable=True))
    op.add_column("tv_shows", sa.Column("backdrop_url", sa.Text(), nullable=True))
    op.add_column("anime", sa.Column("backdrop_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("anime", "backdrop_url")
    op.drop_column("tv_shows", "backdrop_url")
    op.drop_column("movies", "backdrop_url")
