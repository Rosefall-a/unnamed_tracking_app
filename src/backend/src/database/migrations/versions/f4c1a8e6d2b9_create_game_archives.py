"""create game_archives and game_archive_versions

Revision ID: f4c1a8e6d2b9
Revises: a7d2e5c8f3b1
Create Date: 2026-09-09

A named save slot (e.g. "Main World") plus its full upload history — the
old convention of "a save is just an anonymous uploaded file" meant
re-uploading silently discarded the previous one. Scoped to kind in
("save", "world_save"); docs/modpacks stay on the simpler flat file system.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f4c1a8e6d2b9"
down_revision: Union[str, None] = "a7d2e5c8f3b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "game_archives",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_game_archives_game_id", "game_archives", ["game_id"])

    op.create_table(
        "game_archive_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "archive_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_archives.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("size", sa.BigInteger(), nullable=False),
        sa.Column("uploaded_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_game_archive_versions_archive_id", "game_archive_versions", ["archive_id"])


def downgrade() -> None:
    op.drop_index("ix_game_archive_versions_archive_id", table_name="game_archive_versions")
    op.drop_table("game_archive_versions")
    op.drop_index("ix_game_archives_game_id", table_name="game_archives")
    op.drop_table("game_archives")
