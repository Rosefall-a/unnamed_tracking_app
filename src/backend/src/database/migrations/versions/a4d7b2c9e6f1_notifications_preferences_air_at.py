"""notifications, user preferences, exact episode air times, system lists

Revision ID: a4d7b2c9e6f1
Revises: e5a7c2d9f1b3
Create Date: 2026-09-19
"""

import re
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a4d7b2c9e6f1"
down_revision: Union[str, None] = "e5a7c2d9f1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_LABELS = {
    "WISHLIST": "Plan to Watch",
    "WATCHLIST": "Plan to Watch",
    "BACKLOG": "On Hold",
    "IN_PROGRESS": "Watching",
    "REWATCH": "Watching",
    "WATCHED": "Completed",
    "FAVORITE": "Completed",
    "DROPPED": "Dropped",
}


def _relabel(detail: str) -> str:
    """Old history rows stored the raw status names ("WISHLIST -> IN_PROGRESS");
    the app shows Plan to Watch / Watching / etc., so the history should too."""
    text = detail
    for raw, label in _LABELS.items():
        text = re.sub(rf"\b{raw}\b", label, text, flags=re.IGNORECASE)
        text = re.sub(rf"\b{raw.lower().replace('_', ' ')}\b", label, text, flags=re.IGNORECASE)
    return text.replace("->", "→")


def upgrade() -> None:
    op.add_column("anime_episodes", sa.Column("air_at", sa.BigInteger(), nullable=True))
    op.add_column("tv_episodes", sa.Column("air_at", sa.BigInteger(), nullable=True))
    op.add_column(
        "media_lists",
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default="false"),
    )

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("media_type", sa.String(10), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("poster_url", sa.Text(), nullable=True),
        sa.Column("event_at", sa.BigInteger(), nullable=False),
        sa.Column("dedupe_key", sa.String(200), nullable=False),
        sa.Column("read_at", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("user_id", "dedupe_key", name="uq_notifications_user_dedupe"),
    )
    op.create_index("ix_notifications_user_event", "notifications", ["user_id", "event_at"])

    op.create_table(
        "user_preferences",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default="{}"),
    )

    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, detail FROM activity_log WHERE event_type = 'STATUS_CHANGED' AND detail IS NOT NULL")
    ).fetchall()
    for row_id, detail in rows:
        fixed = _relabel(detail)
        if fixed != detail:
            bind.execute(sa.text("UPDATE activity_log SET detail = :d WHERE id = :i"), {"d": fixed, "i": row_id})


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_index("ix_notifications_user_event", table_name="notifications")
    op.drop_table("notifications")
    op.drop_column("media_lists", "is_system")
    op.drop_column("tv_episodes", "air_at")
    op.drop_column("anime_episodes", "air_at")
