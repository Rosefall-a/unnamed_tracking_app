"""Reconcile published final-main and native-interface histories.

Revision ID: b57b38daf5b5
Revises: 2fc5376ef6b5, 53555aee2681
"""

from collections.abc import Sequence

revision: str = "b57b38daf5b5"
down_revision: str | tuple[str, ...] | None = ("2fc5376ef6b5", "53555aee2681")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join upgrade paths without changing metadata, grants or appearance."""


def downgrade() -> None:
    """Restore the published predecessor identities without data changes."""
