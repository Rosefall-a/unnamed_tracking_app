"""replace screenshot tags array with a proper tag table

Revision ID: 7b1e4f9c2a63
Revises: f3a9c2e14d77
Create Date: 2026-09-04 00:00:00.000000

"""

import time
from typing import Sequence, Union
from uuid import uuid4

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "7b1e4f9c2a63"
down_revision: Union[str, None] = "f3a9c2e14d77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "screenshot_tags",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_screenshot_tags_user_id_name"),
    )
    op.create_index("ix_screenshot_tags_user_id", "screenshot_tags", ["user_id"])

    op.create_table(
        "screenshot_tag_links",
        sa.Column("screenshot_id", sa.UUID(), nullable=False),
        sa.Column("tag_id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(["screenshot_id"], ["screenshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tag_id"], ["screenshot_tags.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("screenshot_id", "tag_id"),
    )

    # Backfill: turn each screenshot's old `tags` text[] into rows in the new
    # tables, scoped per-user via the screenshot's game. Uses Python-generated
    # UUIDs/timestamps rather than DB functions to stay portable.
    connection = op.get_bind()
    rows = connection.execute(
        sa.text(
            """
            SELECT s.id AS screenshot_id, s.tags AS tags, g.user_id AS user_id
            FROM screenshots s
            JOIN games g ON g.id = s.game_id
            WHERE s.tags IS NOT NULL AND array_length(s.tags, 1) > 0
            """
        )
    ).fetchall()

    tag_id_cache: dict[tuple, object] = {}
    for row in rows:
        for raw_name in row.tags:
            name = raw_name.strip()
            if not name:
                continue

            cache_key = (row.user_id, name)
            tag_id = tag_id_cache.get(cache_key)
            if tag_id is None:
                existing = connection.execute(
                    sa.text(
                        "SELECT id FROM screenshot_tags WHERE user_id = :user_id AND name = :name"
                    ),
                    {"user_id": row.user_id, "name": name},
                ).fetchone()
                if existing:
                    tag_id = existing.id
                else:
                    tag_id = uuid4()
                    connection.execute(
                        sa.text(
                            "INSERT INTO screenshot_tags (id, user_id, name, created_at) "
                            "VALUES (:id, :user_id, :name, :created_at)"
                        ),
                        {
                            "id": tag_id,
                            "user_id": row.user_id,
                            "name": name,
                            "created_at": int(time.time()),
                        },
                    )
                tag_id_cache[cache_key] = tag_id

            connection.execute(
                sa.text(
                    "INSERT INTO screenshot_tag_links (screenshot_id, tag_id) "
                    "VALUES (:screenshot_id, :tag_id) ON CONFLICT DO NOTHING"
                ),
                {"screenshot_id": row.screenshot_id, "tag_id": tag_id},
            )

    op.drop_column("screenshots", "tags")


def downgrade() -> None:
    op.add_column(
        "screenshots",
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("ARRAY[]::VARCHAR[]"),
        ),
    )

    connection = op.get_bind()
    connection.execute(
        sa.text(
            """
            UPDATE screenshots s
            SET tags = COALESCE(sub.names, ARRAY[]::VARCHAR[])
            FROM (
                SELECT stl.screenshot_id, array_agg(st.name) AS names
                FROM screenshot_tag_links stl
                JOIN screenshot_tags st ON st.id = stl.tag_id
                GROUP BY stl.screenshot_id
            ) sub
            WHERE sub.screenshot_id = s.id
            """
        )
    )
    op.alter_column("screenshots", "tags", server_default=None)

    op.drop_table("screenshot_tag_links")
    op.drop_index("ix_screenshot_tags_user_id", table_name="screenshot_tags")
    op.drop_table("screenshot_tags")
