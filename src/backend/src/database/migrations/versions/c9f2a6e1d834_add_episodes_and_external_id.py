"""add per-episode tables and external_id to tv_shows/anime

Revision ID: c9f2a6e1d834
Revises: b3d7e9f1a5c2
Create Date: 2026-09-13

Adds `tv_episodes` and `anime_episodes` — the optional richer per-episode
breakdown (title, description, air date, thumbnail, watched, rating) that
sits alongside the existing flat `episodes_watched`/`episode_count`
progress numbers on a season, rather than replacing them. Also adds
`external_id` to `tv_shows` and `anime` so a show's episode list can be
synced from the exact right source-provider entry later, instead of
re-searching by title.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c9f2a6e1d834"
down_revision: Union[str, None] = "b3d7e9f1a5c2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("tv_shows", sa.Column("external_id", sa.String(length=50), nullable=True))
    op.add_column("anime", sa.Column("external_id", sa.String(length=50), nullable=True))

    op.create_table(
        "tv_episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "season_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tv_seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("still_url", sa.Text(), nullable=True),
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_tv_episodes_season_id", "tv_episodes", ["season_id"])
    op.create_unique_constraint(
        "uq_tv_episodes_season_id_episode_number", "tv_episodes", ["season_id", "episode_number"]
    )

    op.create_table(
        "anime_episodes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "season_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("anime_seasons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("episode_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("still_url", sa.Text(), nullable=True),
        sa.Column("watched", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("rating", sa.Numeric(4, 2), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_anime_episodes_season_id", "anime_episodes", ["season_id"])
    op.create_unique_constraint(
        "uq_anime_episodes_season_id_episode_number",
        "anime_episodes",
        ["season_id", "episode_number"],
    )


def downgrade() -> None:
    op.drop_table("anime_episodes")
    op.drop_table("tv_episodes")
    op.drop_column("anime", "external_id")
    op.drop_column("tv_shows", "external_id")
