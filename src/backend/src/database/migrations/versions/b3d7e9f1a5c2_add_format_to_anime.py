"""add format to anime

Revision ID: b3d7e9f1a5c2
Revises: e1a4f8c2b7d3
Create Date: 2026-09-13

Adds `anime.format` — the media sub-format (TV, Movie, OVA, ONA, Special,
Music) as reported by AniList/Jikan. The UI was showing a generic "Anime"
label under every title regardless of its real format; this column lets
that label reflect the actual per-title format instead.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3d7e9f1a5c2"
down_revision: Union[str, None] = "e1a4f8c2b7d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anime", sa.Column("format", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("anime", "format")
