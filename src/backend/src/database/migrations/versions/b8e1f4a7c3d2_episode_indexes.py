"""indexes for the statistics and notification queries

Revision ID: b8e1f4a7c3d2
Revises: a4d7b2c9e6f1
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b8e1f4a7c3d2"
down_revision: Union[str, None] = "a4d7b2c9e6f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # statistics: watched episodes per season
    op.create_index("ix_anime_episodes_season_watched", "anime_episodes", ["season_id", "watched"])
    op.create_index("ix_tv_episodes_season_watched", "tv_episodes", ["season_id", "watched"])
    # notifications: episodes that aired inside a recent window (most rows
    # have no air time, so the index only holds the ones that do)
    op.create_index(
        "ix_anime_episodes_air_at", "anime_episodes", ["air_at"], postgresql_where="air_at IS NOT NULL"
    )
    op.create_index(
        "ix_tv_episodes_air_at", "tv_episodes", ["air_at"], postgresql_where="air_at IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_tv_episodes_air_at", table_name="tv_episodes")
    op.drop_index("ix_anime_episodes_air_at", table_name="anime_episodes")
    op.drop_index("ix_tv_episodes_season_watched", table_name="tv_episodes")
    op.drop_index("ix_anime_episodes_season_watched", table_name="anime_episodes")
