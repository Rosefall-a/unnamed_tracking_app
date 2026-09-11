"""add optional Playnite GUID to games

Revision ID: b7e4c2f9a1d6
Revises: a5f8c3e1b746
Create Date: 2026-09-11

Stores the optional GUID of the corresponding Playnite library entry.
Manually-created app games leave this value NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b7e4c2f9a1d6"
down_revision: Union[str, None] = "a5f8c3e1b746"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column("playnite_guid", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("ix_games_playnite_guid", "games", ["playnite_guid"])


def downgrade() -> None:
    op.drop_index("ix_games_playnite_guid", table_name="games")
    op.drop_column("games", "playnite_guid")
