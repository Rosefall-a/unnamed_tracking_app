"""flag the episodes that imported progress already covers

A list imported by number alone (MAL) stored only how many episodes were
watched. When the episode rows were created later they started unflagged, so
the title page showed 0 watched while the library showed all of them. This
flags the lowest-numbered unflagged episodes to cover that counter. Running
it again changes nothing: once the flags match the counter there is nothing
left to cover (see docs/migrations.md).

Revision ID: c2a9e5d1f7b4
Revises: b8e2a6c4d0f9
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c2a9e5d1f7b4"
down_revision: Union[str, None] = "b8e2a6c4d0f9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _flag(episodes: str, seasons: str) -> str:
    return f"""
        WITH ranked AS (
            SELECT e.id,
                   ROW_NUMBER() OVER (PARTITION BY e.season_id ORDER BY e.episode_number) AS rn,
                   s.episodes_watched - (
                       SELECT COUNT(*) FROM {episodes} f WHERE f.season_id = s.id AND f.watched
                   ) AS need
            FROM {episodes} e
            JOIN {seasons} s ON s.id = e.season_id
            WHERE NOT e.watched
        )
        UPDATE {episodes} SET watched = true
        FROM ranked
        WHERE {episodes}.id = ranked.id AND ranked.rn <= ranked.need
        """


def upgrade() -> None:
    op.execute(_flag("anime_episodes", "anime_seasons"))
    op.execute(_flag("tv_episodes", "tv_seasons"))


def downgrade() -> None:
    # the flags cannot be told apart from ones set by hand
    pass
