"""add steamgriddb api key to users

Revision ID: 7a1f4c9d8e21
Revises: 1c6f2e8a9b70
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7a1f4c9d8e21"
down_revision: Union[str, None] = "1c6f2e8a9b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("steamgriddb_api_key", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "steamgriddb_api_key")
