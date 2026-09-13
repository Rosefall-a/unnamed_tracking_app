"""add psn npsso token to users

Revision ID: 3b6d8f0a1c4e
Revises: 7a1f4c9d8e21
Create Date: 2026-09-04

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3b6d8f0a1c4e"
down_revision: Union[str, None] = "7a1f4c9d8e21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("psn_npsso_token", sa.Text(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("psn_validated_at", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "psn_validated_at")
    op.drop_column("users", "psn_npsso_token")
