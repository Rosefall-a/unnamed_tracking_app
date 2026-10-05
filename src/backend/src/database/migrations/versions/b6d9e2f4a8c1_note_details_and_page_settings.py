"""Note details and versions, and per-game page settings.

game_note_details holds what a markdown note has beyond its text (created date,
pin, tags, the achievement it is about), game_note_versions keeps earlier
states of a note so edits can be undone, and games.page_settings holds a
game's overrides of the page defaults (which tabs show, and so on).

Create-if-missing, so this is safe on a database adopted from an older history
(see src/database/migrate.py).

revision: b6d9e2f4a8c1
down_revision: a9d3e5c7b1f2
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from src.database import migration_helpers as h

revision: str = "b6d9e2f4a8c1"
down_revision: str | None = "a9d3e5c7b1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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
        sa.Column(
            "tags",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
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
    h.add_column_if_missing(
        "games", sa.Column("page_settings", postgresql.JSONB(), nullable=True)
    )


def downgrade() -> None:
    pass
