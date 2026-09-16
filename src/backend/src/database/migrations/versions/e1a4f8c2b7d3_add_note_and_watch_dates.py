"""add note, start_date and end_date to movies/tv_shows/anime

Revision ID: e1a4f8c2b7d3
Revises: c7e2a4f9b316
Create Date: 2026-09-13

Adds a free-text personal note and start/end watch dates to all three
media entities — the library redesign work needs somewhere to store a
per-title note (shown/edited from the library grid, not just the detail
page) and the date range a user actually watched something, matching the
same fields MAL/AniList expose on their own list entries.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e1a4f8c2b7d3"
down_revision: Union[str, None] = "c7e2a4f9b316"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ["movies", "tv_shows", "anime"]


def upgrade() -> None:
    for table in _TABLES:
        op.add_column(table, sa.Column("note", sa.Text(), nullable=True))
        op.add_column(table, sa.Column("start_date", sa.Date(), nullable=True))
        op.add_column(table, sa.Column("end_date", sa.Date(), nullable=True))


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.drop_column(table, "end_date")
        op.drop_column(table, "start_date")
        op.drop_column(table, "note")
