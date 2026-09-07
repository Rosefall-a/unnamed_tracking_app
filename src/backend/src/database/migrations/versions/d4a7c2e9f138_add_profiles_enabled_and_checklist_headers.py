"""add games.profiles_enabled and game_checklist_items.is_header

Revision ID: d4a7c2e9f138
Revises: c1f9b3d7e582
Create Date: 2026-09-06

profiles_enabled is a per-game opt-in (default off) for the account/profile
switcher, so a multi-account game like OSRS can turn it on without every
other game showing an account chip bar it'll never use.

is_header lets a checklist item act as a section divider (e.g. "Quest cape
reqs") in the same ordered list as real items, instead of a separate table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d4a7c2e9f138"
down_revision: Union[str, None] = "c1f9b3d7e582"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games", sa.Column("profiles_enabled", sa.Boolean(), nullable=False, server_default=sa.false())
    )
    op.add_column(
        "game_checklist_items", sa.Column("is_header", sa.Boolean(), nullable=False, server_default=sa.false())
    )


def downgrade() -> None:
    op.drop_column("game_checklist_items", "is_header")
    op.drop_column("games", "profiles_enabled")
