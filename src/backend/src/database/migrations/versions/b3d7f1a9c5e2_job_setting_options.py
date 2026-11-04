"""Extra per-job settings, such as how many automatic backups to keep; and
game links now go with their game, which let an admin delete an account
(the old foreign key blocked the account's games from being removed).

Revision ID: b3d7f1a9c5e2
Revises: a9c3e5b7d2f4
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from src.database import migration_helpers as h

revision: str = "b3d7f1a9c5e2"
down_revision: str | None = "a9c3e5b7d2f4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_LINKS_FK = "game_links_game_id_fkey"


def upgrade() -> None:
    h.add_column_if_missing("job_settings", sa.Column("options", JSONB, nullable=True))
    if h.has_constraint(_LINKS_FK):
        op.drop_constraint(_LINKS_FK, "game_links", type_="foreignkey")
    op.create_foreign_key(_LINKS_FK, "game_links", "games", ["game_id"], ["id"], ondelete="CASCADE")


def downgrade() -> None:
    op.drop_constraint(_LINKS_FK, "game_links", type_="foreignkey")
    op.create_foreign_key(_LINKS_FK, "game_links", "games", ["game_id"], ["id"])
    op.drop_column("job_settings", "options")
