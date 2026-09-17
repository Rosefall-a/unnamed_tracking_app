"""clear "Untitled" episode titles

Revision ID: b6e1a3f9c7d2
Revises: a7c4e1f8b3d5
Create Date: 2026-09-16

AniList's streamingEpisodes sometimes literally returns the string
"Untitled" instead of leaving an episode's title blank when its
streaming partner didn't supply one. That placeholder was being stored
as a real title, which blocked every other source (Jikan, TMDB) from
ever filling in the real one -- the backfill/merge logic treats "has a
title" as done. Clears existing "Untitled" rows back to NULL so they're
eligible for a real title on the next refresh; no downgrade equivalent
since the original placeholder carried no information worth restoring.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b6e1a3f9c7d2"
down_revision: Union[str, None] = "a7c4e1f8b3d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE anime_episodes SET title = NULL WHERE lower(title) = 'untitled'"
    )


def downgrade() -> None:
    pass
