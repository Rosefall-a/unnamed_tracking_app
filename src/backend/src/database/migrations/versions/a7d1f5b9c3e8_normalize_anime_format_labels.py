"""store an anime's format with the same label whichever way it was added

The MyAnimeList import wrote MOVIE, SPECIAL and MUSIC in capitals while the
AniList lookup writes Movie, Special and Music, so the same kind of title read
two ways and filtered as two formats. Rewriting them is safe to repeat (see
docs/migrations.md).

Revision ID: a7d1f5b9c3e8
Revises: f5b9d3a7c1e6
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a7d1f5b9c3e8"
down_revision: Union[str, None] = "f5b9d3a7c1e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE anime SET format = CASE format
            WHEN 'MOVIE' THEN 'Movie'
            WHEN 'SPECIAL' THEN 'Special'
            WHEN 'MUSIC' THEN 'Music'
            WHEN 'TV_SHORT' THEN 'TV Short'
        END
        WHERE format IN ('MOVIE', 'SPECIAL', 'MUSIC', 'TV_SHORT')
        """
    )


def downgrade() -> None:
    pass
