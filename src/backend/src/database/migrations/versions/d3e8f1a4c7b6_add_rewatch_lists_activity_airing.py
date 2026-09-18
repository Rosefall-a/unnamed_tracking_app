"""add rewatch log, media lists, activity log, airing dates, anime cross-links

Revision ID: d3e8f1a4c7b6
Revises: c4f8a2e6b9d1
Create Date: 2026-09-17

Adds the schema for six requested features:
- rewatch_logs: dated rewatch history (Movie/TVShow/Anime.rewatches
  stays the fast denormalized count; this is when each one happened).
- media_lists / media_list_items: user-named custom groupings across
  all three media types.
- activity_log: a day-granular history feed (one row per
  user/media/event-type/day, not per action).
- anime.next_episode_air_at/next_episode_number,
  tv_shows.next_episode_air_at/next_episode_number: real airing
  timestamps for a countdown display and the calendar view (is_airing
  already existed as a bare yes/no flag).
- anime.linked_tv_show_id/linked_movie_id: a manual cross-link to a
  live-action adaptation or source, deliberately not auto-detected.

`media_type`/`event_type` are plain VARCHAR, not native Postgres ENUM
types — matches every other status/enum column in this codebase
(`native_enum=False` on the model side, e.g. AnimeStatus), which stores
as a string with the choices enforced in the Python/Pydantic layer
rather than a DB-level type. Keeps this migration to plain column DDL
with no CREATE TYPE lifecycle to manage.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d3e8f1a4c7b6"
down_revision: Union[str, None] = "c4f8a2e6b9d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rewatch_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("finished_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_rewatch_logs_user_id", "rewatch_logs", ["user_id"])
    op.create_index("ix_rewatch_logs_media_id", "rewatch_logs", ["media_id"])

    op.create_table(
        "media_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "name", name="uq_media_lists_user_id_name"),
    )
    op.create_index("ix_media_lists_user_id", "media_lists", ["user_id"])

    op.create_table(
        "media_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("media_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("added_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "list_id", "media_type", "media_id", name="uq_media_list_items_list_media"
        ),
    )
    op.create_index("ix_media_list_items_list_id", "media_list_items", ["list_id"])
    op.create_index("ix_media_list_items_media_id", "media_list_items", ["media_id"])

    op.create_table(
        "activity_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("media_type", sa.String(length=10), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_title", sa.String(length=500), nullable=False),
        sa.Column("event_type", sa.String(length=20), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("count", sa.BigInteger(), nullable=False, server_default="1"),
        sa.Column("detail", sa.String(length=200), nullable=True),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "media_type", "media_id", "event_type", "event_date",
            name="uq_activity_log_bucket",
        ),
    )
    op.create_index("ix_activity_log_user_id", "activity_log", ["user_id"])
    op.create_index(
        "ix_activity_log_user_event_date", "activity_log", ["user_id", "event_date"]
    )

    op.add_column("anime", sa.Column("next_episode_air_at", sa.BigInteger(), nullable=True))
    op.add_column("anime", sa.Column("next_episode_number", sa.Integer(), nullable=True))
    op.add_column(
        "anime",
        sa.Column(
            "linked_tv_show_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("tv_shows.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "anime",
        sa.Column(
            "linked_movie_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("movies.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    op.add_column("tv_shows", sa.Column("next_episode_air_at", sa.BigInteger(), nullable=True))
    op.add_column("tv_shows", sa.Column("next_episode_number", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("tv_shows", "next_episode_number")
    op.drop_column("tv_shows", "next_episode_air_at")

    op.drop_column("anime", "linked_movie_id")
    op.drop_column("anime", "linked_tv_show_id")
    op.drop_column("anime", "next_episode_number")
    op.drop_column("anime", "next_episode_air_at")

    op.drop_index("ix_activity_log_user_event_date", table_name="activity_log")
    op.drop_index("ix_activity_log_user_id", table_name="activity_log")
    op.drop_table("activity_log")

    op.drop_index("ix_media_list_items_media_id", table_name="media_list_items")
    op.drop_index("ix_media_list_items_list_id", table_name="media_list_items")
    op.drop_table("media_list_items")

    op.drop_index("ix_media_lists_user_id", table_name="media_lists")
    op.drop_table("media_lists")

    op.drop_index("ix_rewatch_logs_media_id", table_name="rewatch_logs")
    op.drop_index("ix_rewatch_logs_user_id", table_name="rewatch_logs")
    op.drop_table("rewatch_logs")
