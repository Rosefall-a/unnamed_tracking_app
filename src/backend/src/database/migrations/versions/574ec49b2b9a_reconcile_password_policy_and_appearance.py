"""reconcile password policy and appearance

Revision ID: 574ec49b2b9a
Revises: c5f8b3a1d204, d3b7e8a9c602
Create Date: 2026-10-05 11:35:31.113273

"""
from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "574ec49b2b9a"
down_revision: Union[str, tuple[str, str], None] = ("c5f8b3a1d204", "d3b7e8a9c602")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Join both histories without changing schema or retained legacy data."""


def downgrade() -> None:
    """Restore the two prior revision markers without changing data."""
