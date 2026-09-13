"""create tv_shows and tv_seasons

Revision ID: a9f3d6c2e841
Revises: d8f1c3a6b295
Create Date: 2026-09-12

TV Shows, mirroring the Movies table shape (see
d8f1c3a6b295_add_movie_poster_and_metadata_keys) with TV-specific swaps:
episode_runtime_minutes instead of a single runtime, creators instead of
director/writer. tv_seasons is a real child table (not a count column) —
each season carries its own metadata (episode_count from the provider)
alongside the user's own watch progress (episodes_watched), so a season
can be tracked independently of the show's overall status.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a9f3d6c2e841"
down_revision: Union[str, None] = "d8f1c3a6b295"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tv_shows",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("sort_title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("first_air_date", sa.Date(), nullable=True),
        sa.Column("episode_runtime_minutes", sa.Integer(), nullable=True),
        sa.Column("creators", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("studios", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("countries", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("languages", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("genres", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("features", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("age_rating", sa.String(length=20), nullable=True),
        sa.Column("tmdb_score", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "DROPPED",
                "WISHLIST",
                "WATCHLIST",
                "BACKLOG",
                "IN_PROGRESS",
                "WATCHED",
                "FAVORITE",
                "REWATCH",
                name="tvshowstatus",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("priority", sa.String(length=20), nullable=True),
        sa.Column("favorite", sa.Boolean(), nullable=False),
        sa.Column("rewatches", sa.Integer(), nullable=False),
        sa.Column("rating_story", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("rating_performance", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("rating_soundtrack", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("rating_overall", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("personal_rank", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_tv_shows_user_id", "tv_shows", ["user_id"])

    op.create_table(
        "tv_seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "show_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tv_shows.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("season_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=True),
        sa.Column("episode_count", sa.Integer(), nullable=True),
        sa.Column("episodes_watched", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "status",
            sa.Enum(
                "DROPPED",
                "WISHLIST",
                "WATCHLIST",
                "BACKLOG",
                "IN_PROGRESS",
                "WATCHED",
                "FAVORITE",
                "REWATCH",
                name="tvseasonstatus",
                native_enum=False,
                length=30,
            ),
            nullable=False,
        ),
        sa.Column("air_date", sa.Date(), nullable=True),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_tv_seasons_show_id", "tv_seasons", ["show_id"])


def downgrade() -> None:
    op.drop_index("ix_tv_seasons_show_id", table_name="tv_seasons")
    op.drop_table("tv_seasons")
    op.drop_index("ix_tv_shows_user_id", table_name="tv_shows")
    op.drop_table("tv_shows")
