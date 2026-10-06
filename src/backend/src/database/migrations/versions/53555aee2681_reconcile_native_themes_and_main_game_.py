"""Reconcile published native-theme and main game-page histories.

Revision ID: 53555aee2681
Revises: 7392033bd0f4, 574ec49b2b9a
"""

from collections.abc import Sequence

revision: str = "53555aee2681"
down_revision: str | tuple[str, ...] | None = ("7392033bd0f4", "574ec49b2b9a")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Join upgrade paths without changing schema or personal themes."""


def downgrade() -> None:
    """Retain the published predecessor identities without data changes."""
