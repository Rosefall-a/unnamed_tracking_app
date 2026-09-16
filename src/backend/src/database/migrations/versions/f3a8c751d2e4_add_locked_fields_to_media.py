"""add locked_fields to movies, tv_shows, anime

Revision ID: f3a8c751d2e4
Revises: b7e4d2a9c168
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "f3a8c751d2e4"
down_revision: Union[str, None] = "b7e4d2a9c168"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    for table in ("movies", "tv_shows", "anime"):
        op.add_column(
            table,
            sa.Column(
                "locked_fields",
                postgresql.ARRAY(sa.String()),
                nullable=False,
                server_default="{}",
            ),
        )


def downgrade() -> None:
    for table in ("movies", "tv_shows", "anime"):
        op.drop_column(table, "locked_fields")
