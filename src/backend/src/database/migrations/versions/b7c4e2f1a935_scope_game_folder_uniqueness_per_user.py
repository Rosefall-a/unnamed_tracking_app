"""scope active game folder uniqueness per user

Revision ID: b7c4e2f1a935
Revises: a5f8c3e1b746
Create Date: 2026-09-11

Game folder names are stored inside a user-specific filesystem namespace,
so the database uniqueness constraint must also be scoped by user_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b7c4e2f1a935"
down_revision: Union[str, None] = "a5f8c3e1b746"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_games_folder_location_active", table_name="games")
    op.create_index(
        "ix_games_user_folder_location_active",
        "games",
        ["user_id", "folder_location"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_games_user_folder_location_active", table_name="games")
    op.create_index(
        "ix_games_folder_location_active",
        "games",
        ["folder_location"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
