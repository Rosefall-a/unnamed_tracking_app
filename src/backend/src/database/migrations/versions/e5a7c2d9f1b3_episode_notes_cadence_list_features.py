"""episode notes, per-show airing cadence, smart/ordered lists, calendar feed token

Revision ID: e5a7c2d9f1b3
Revises: d3e8f1a4c7b6
Create Date: 2026-09-18
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e5a7c2d9f1b3"
down_revision: Union[str, None] = "d3e8f1a4c7b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("anime", sa.Column("airing_interval_days", sa.Integer(), nullable=True))
    op.add_column("tv_shows", sa.Column("airing_interval_days", sa.Integer(), nullable=True))
    op.add_column("anime_episodes", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("tv_episodes", sa.Column("note", sa.Text(), nullable=True))
    op.add_column("media_lists", sa.Column("smart_rule", postgresql.JSONB(), nullable=True))
    op.add_column("media_lists", sa.Column("cover_media_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column(
        "media_list_items",
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column("users", sa.Column("calendar_token", sa.String(length=64), nullable=True))
    op.create_unique_constraint("uq_users_calendar_token", "users", ["calendar_token"])


def downgrade() -> None:
    op.drop_constraint("uq_users_calendar_token", "users", type_="unique")
    op.drop_column("users", "calendar_token")
    op.drop_column("media_list_items", "position")
    op.drop_column("media_lists", "cover_media_id")
    op.drop_column("media_lists", "smart_rule")
    op.drop_column("tv_episodes", "note")
    op.drop_column("anime_episodes", "note")
    op.drop_column("tv_shows", "airing_interval_days")
    op.drop_column("anime", "airing_interval_days")
