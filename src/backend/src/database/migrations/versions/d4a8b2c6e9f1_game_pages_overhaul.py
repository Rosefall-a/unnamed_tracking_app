"""Everything the game pages overhaul stores.

Achievements gain a hidden flag (providers mark spoilers) and a global percent
(how many players have each). Screenshots, clips, soundtrack and the inbox gain
an in-app title and a real "taken" date with where that date came from, and
clips gain a saved thumbnail and length. Docs and modpack files get the same
title, note, tags and date. Saves and worlds gain a note and tags. Notes get a
details table (created date, pin, tags, the achievement they are about) and a
versions table for undo, and games get per-game page settings.

Everything is create-if-missing, so this is safe on a database adopted from an
older history (see src/database/migrate.py). Existing rows keep their old
values: new columns start empty and fill in as things are used or synced.

revision: d4a8b2c6e9f1
down_revision: c4f7a1d2e6b8
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "d4a8b2c6e9f1"
down_revision: str | None = "c4f7a1d2e6b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _tags_column() -> sa.Column:
    return sa.Column(
        "tags",
        postgresql.ARRAY(sa.String()),
        nullable=False,
        server_default=sa.text("'{}'"),
    )


def upgrade() -> None:
    # achievements: which ones a provider hides, and how common each is
    h.add_column_if_missing(
        "achievements",
        sa.Column("hidden", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    h.add_column_if_missing("achievements", sa.Column("global_percent", sa.Float(), nullable=True))

    # screenshots, clips and soundtrack: a title, a real taken date, clip previews
    h.add_column_if_missing("media_items", sa.Column("title", sa.String(200), nullable=True))
    h.add_column_if_missing("media_items", sa.Column("taken_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing("media_items", sa.Column("taken_source", sa.String(20), nullable=True))
    h.add_column_if_missing(
        "media_items", sa.Column("thumb_filename", sa.String(300), nullable=True)
    )
    h.add_column_if_missing("media_items", sa.Column("duration", sa.Float(), nullable=True))
    h.add_column_if_missing("inbox_items", sa.Column("taken_at", sa.BigInteger(), nullable=True))
    h.add_column_if_missing("inbox_items", sa.Column("taken_source", sa.String(20), nullable=True))

    # docs and modpack files work like the screenshots gallery
    h.add_column_if_missing("game_file_items", sa.Column("title", sa.String(200), nullable=True))
    h.add_column_if_missing("game_file_items", sa.Column("note", sa.Text(), nullable=True))
    h.add_column_if_missing("game_file_items", _tags_column())
    h.add_column_if_missing(
        "game_file_items", sa.Column("taken_at", sa.BigInteger(), nullable=True)
    )
    h.add_column_if_missing(
        "game_file_items", sa.Column("taken_source", sa.String(20), nullable=True)
    )

    # saves and worlds can be described and sorted
    h.add_column_if_missing("game_archives", sa.Column("note", sa.Text(), nullable=True))
    h.add_column_if_missing("game_archives", _tags_column())

    # notes: details beyond their text, and earlier versions
    h.create_table_if_missing(
        "game_note_details",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "game_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("games.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        _tags_column(),
        sa.Column(
            "linked_achievement_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("achievements.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.UniqueConstraint("game_id", "name", name="uq_game_note_details_game_name"),
    )
    h.create_index_if_missing("ix_game_note_details_game_id", "game_note_details", ["game_id"])
    h.create_table_if_missing(
        "game_note_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "note_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("game_note_details.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("saved_at", sa.BigInteger(), nullable=False),
    )
    h.create_index_if_missing("ix_game_note_versions_note_id", "game_note_versions", ["note_id"])

    # per-game overrides of the page defaults (which tabs show, and so on)
    h.add_column_if_missing("games", sa.Column("page_settings", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.execute("ALTER TABLE games DROP COLUMN IF EXISTS page_settings")
    op.execute("DROP TABLE IF EXISTS game_note_versions")
    op.execute("DROP TABLE IF EXISTS game_note_details")
    op.execute("ALTER TABLE game_archives DROP COLUMN IF EXISTS tags, DROP COLUMN IF EXISTS note")
    op.execute(
        "ALTER TABLE game_file_items DROP COLUMN IF EXISTS taken_source,"
        " DROP COLUMN IF EXISTS taken_at, DROP COLUMN IF EXISTS tags,"
        " DROP COLUMN IF EXISTS note, DROP COLUMN IF EXISTS title"
    )
    op.execute(
        "ALTER TABLE inbox_items DROP COLUMN IF EXISTS taken_source, DROP COLUMN IF EXISTS taken_at"
    )
    op.execute(
        "ALTER TABLE media_items DROP COLUMN IF EXISTS duration,"
        " DROP COLUMN IF EXISTS thumb_filename, DROP COLUMN IF EXISTS taken_source,"
        " DROP COLUMN IF EXISTS taken_at, DROP COLUMN IF EXISTS title"
    )
    op.execute(
        "ALTER TABLE achievements DROP COLUMN IF EXISTS global_percent, DROP COLUMN IF EXISTS hidden"
    )
