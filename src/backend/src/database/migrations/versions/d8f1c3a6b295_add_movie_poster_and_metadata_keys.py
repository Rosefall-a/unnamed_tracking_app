"""add movie poster_url and tmdb/omdb metadata keys

Revision ID: d8f1c3a6b295
Revises: c2e5a9f4d817
Create Date: 2026-09-11

Adds a direct external poster URL to movies (TMDB's CDN / OMDb's Poster
field, never downloaded — see database/models/movies.py) and the two
deployment-wide metadata provider keys movie search needs, following the
same Fernet-encrypted, never-echoed pattern as igdb_client_secret.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d8f1c3a6b295"
down_revision: Union[str, None] = "c2e5a9f4d817"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("movies", sa.Column("poster_url", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("tmdb_api_key", sa.Text(), nullable=True))
    op.add_column("app_integration_settings", sa.Column("omdb_api_key", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("app_integration_settings", "omdb_api_key")
    op.drop_column("app_integration_settings", "tmdb_api_key")
    op.drop_column("movies", "poster_url")
