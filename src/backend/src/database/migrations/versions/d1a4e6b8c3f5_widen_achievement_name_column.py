"""widen achievements.name to unbounded text

Revision ID: d1a4e6b8c3f5
Revises: c6a8f2e4b9d3
Create Date: 2026-09-04

Steam's achievement names hit VARCHAR(300) during a real library sync
(Cookie Clicker's 637-achievement list), aborting the whole insert batch.
name now matches description/icon_url as unbounded Text.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "d1a4e6b8c3f5"
down_revision: Union[str, None] = "c6a8f2e4b9d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("achievements", "name", type_=sa.Text(), existing_type=sa.String(300), existing_nullable=False)


def downgrade() -> None:
    op.alter_column(
        "achievements", "name", type_=sa.String(300), existing_type=sa.Text(), existing_nullable=False
    )
