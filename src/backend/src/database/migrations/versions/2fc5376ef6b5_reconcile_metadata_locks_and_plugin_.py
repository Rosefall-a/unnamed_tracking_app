"""Reconcile published metadata-lock and plugin-manager histories.

Revision ID: 2fc5376ef6b5
Revises: 7392033bd0f4, c4f1d2e8a9b0
"""

from collections.abc import Sequence

revision: str = "2fc5376ef6b5"
down_revision: str | tuple[str, ...] | None = ("7392033bd0f4", "c4f1d2e8a9b0")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join upgrade paths without changing schema or data."""


def downgrade() -> None:
    """Restore the published predecessor identities without data changes."""
