"""Reconcile session network metadata with main.

Revision ID: 65acf36995e5
Revises: b57b38daf5b5, f2a8c9d0e1b2
Create Date: 2026-10-06 19:57:47.205721

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "65acf36995e5"
down_revision: tuple[str, ...] = ("b57b38daf5b5", "f2a8c9d0e1b2")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join existing upgrade paths without schema or data changes."""


def downgrade() -> None:
    """Restore predecessor revision identities without schema or data changes."""
