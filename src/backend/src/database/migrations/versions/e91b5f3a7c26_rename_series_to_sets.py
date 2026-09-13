"""rename series to sets, drop games.series_id

Revision ID: e91b5f3a7c26
Revises: d4a8e6c2f951
Create Date: 2026-09-09

Terminology fix: the design spec calls this concept "Set", never "Series"
(Set System, Set Symbol, "07/24" set position). Renamed in place rather
than dropped and recreated, so any set already created in dev testing
survives. Also drops games.series_id entirely — per the spec, set
membership ("07/24") is collector-footer information a *card* carries, not
a property of the game itself, so the only link going forward is the new
cards.set_id (see create_cards_table). Table name is plural "sets", not
the reserved word "set", matching this codebase's existing pluralized
table convention (games, users, bounties).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "e91b5f3a7c26"
down_revision: Union[str, None] = "d4a8e6c2f951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("games_series_id_fkey", "games", type_="foreignkey")
    op.drop_index("ix_games_series_id", table_name="games")
    op.drop_column("games", "series_id")

    op.rename_table("series", "sets")
    op.execute("ALTER INDEX ix_series_user_id RENAME TO ix_sets_user_id")
    op.execute("ALTER TABLE sets RENAME CONSTRAINT uq_series_user_id_name TO uq_sets_user_id_name")
    op.execute("ALTER TABLE sets RENAME CONSTRAINT series_user_id_fkey TO sets_user_id_fkey")
    op.execute("ALTER INDEX series_pkey RENAME TO sets_pkey")


def downgrade() -> None:
    op.execute("ALTER INDEX sets_pkey RENAME TO series_pkey")
    op.execute("ALTER TABLE sets RENAME CONSTRAINT sets_user_id_fkey TO series_user_id_fkey")
    op.execute("ALTER TABLE sets RENAME CONSTRAINT uq_sets_user_id_name TO uq_series_user_id_name")
    op.execute("ALTER INDEX ix_sets_user_id RENAME TO ix_series_user_id")
    op.rename_table("sets", "series")

    op.add_column(
        "games",
        sa.Column("series_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_games_series_id", "games", ["series_id"])
    op.create_foreign_key(
        "games_series_id_fkey", "games", "series", ["series_id"], ["id"], ondelete="SET NULL"
    )
