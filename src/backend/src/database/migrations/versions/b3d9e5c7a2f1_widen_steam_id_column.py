"""widen users.steam_id to fit a full profile URL

Revision ID: b3d9e5c7a2f1
Revises: f2c8a4e6d1b7
Create Date: 2026-09-04

The Steam library-sync field accepts a profile URL, vanity name, or raw
SteamID64 and resolves it server-side — a URL can be well over the original
32-char limit sized for just the bare numeric ID.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b3d9e5c7a2f1"
down_revision: Union[str, None] = "f2c8a4e6d1b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("users", "steam_id", type_=sa.String(255), existing_type=sa.String(32))


def downgrade() -> None:
    op.alter_column("users", "steam_id", type_=sa.String(32), existing_type=sa.String(255))
