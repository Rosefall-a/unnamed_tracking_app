"""add collections to games

Revision ID: b6e2c8a4d1f7
Revises: a3d7f1c9e5b2
Create Date: 2026-09-06

Collections were entirely a frontend mock-data stub before this — adding a
game to a collection against the real backend just threw
"Collections are not supported by the backend yet." Same shape as
tags/features (a plain string array on the game), not a join table.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b6e2c8a4d1f7"
down_revision: Union[str, None] = "a3d7f1c9e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "games",
        sa.Column(
            "collections", postgresql.ARRAY(sa.String()), nullable=False, server_default="{}"
        ),
    )


def downgrade() -> None:
    op.drop_column("games", "collections")
