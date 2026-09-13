"""add oidc identity and allow first-run setup without env credentials

Revision ID: 7a2c1b9e4d10
Revises: 1c6f2e8a9b70
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "7a2c1b9e4d10"
down_revision: Union[str, None] = "1c6f2e8a9b70"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("oidc_subject", sa.String(length=512), nullable=True))
    op.create_unique_constraint("uq_users_oidc_subject", "users", ["oidc_subject"])


def downgrade() -> None:
    op.drop_constraint("uq_users_oidc_subject", "users", type_="unique")
    op.drop_column("users", "oidc_subject")
