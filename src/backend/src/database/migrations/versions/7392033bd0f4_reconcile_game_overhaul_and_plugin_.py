"""reconcile game overhaul and plugin manager

Revision ID: 7392033bd0f4
Revises: c5f8b3a1d204, 8c7e1a4d2b90
Create Date: 2026-10-06 12:55:30.253383

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "7392033bd0f4"
down_revision: str | tuple[str, ...] | None = ("c5f8b3a1d204", "8c7e1a4d2b90")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join published histories without changing data or revision identities."""


def downgrade() -> None:
    """Retain each predecessor when separating the published upgrade paths."""
