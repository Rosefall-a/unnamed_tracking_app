"""add provider display identity (persona name + avatar) to users

Revision ID: e4b7c9f1a2d6
Revises: d1a4e6b8c3f5
Create Date: 2026-09-04

Lets Settings show who is connected on each account tile (name + avatar)
instead of only a green "Connected" dot.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e4b7c9f1a2d6"
down_revision: Union[str, None] = "d1a4e6b8c3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("steam_persona_name", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("steam_avatar_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("retroachievements_avatar_url", sa.Text(), nullable=True))
    op.add_column("users", sa.Column("psn_online_id", sa.String(length=128), nullable=True))
    op.add_column("users", sa.Column("psn_avatar_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "psn_avatar_url")
    op.drop_column("users", "psn_online_id")
    op.drop_column("users", "retroachievements_avatar_url")
    op.drop_column("users", "steam_avatar_url")
    op.drop_column("users", "steam_persona_name")
