"""create anime and anime_seasons

Revision ID: c7e2a4f9b316
Revises: a9f3d6c2e841
Create Date: 2026-09-13

Anime, mirroring TV Shows' table shape (see
a9f3d6c2e841_create_tv_shows_and_seasons) with anime-specific swaps:
anilist_score/mal_score instead of a single tmdb_score, studios instead
of creators as the primary credited-work field. anime_seasons exists for
the same reason tv_seasons does (a real child table, not a count), even
though many anime don't split into TV-style seasons the way Western
shows do — a cour is often its own separate AniList entry rather than a
season of an existing one, so most anime rows will carry exactly one
season in practice.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c7e2a4f9b316"
down_revision: Union[str, None] = "a9f3d6c2e841"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "anime",
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
        sa.Column("studios", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("countries", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("languages", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("genres", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("tags", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("features", sa.ARRAY(sa.String()), nullable=False, server_default="{}"),
        sa.Column("age_rating", sa.String(length=20), nullable=True),
        sa.Column("anilist_score", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("mal_score", sa.Numeric(precision=4, scale=2), nullable=True),
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
                name="animestatus",
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
    op.create_index("ix_anime_user_id", "anime", ["user_id"])

    op.create_table(
        "anime_seasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "show_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("anime.id", ondelete="CASCADE"),
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
                name="animeseasonstatus",
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
    op.create_index("ix_anime_seasons_show_id", "anime_seasons", ["show_id"])


def downgrade() -> None:
    op.drop_index("ix_anime_seasons_show_id", table_name="anime_seasons")
    op.drop_table("anime_seasons")
    op.drop_index("ix_anime_user_id", table_name="anime")
    op.drop_table("anime")
