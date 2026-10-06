"""Reconcile the independently published main and plugin-manager histories.

Both upgrade paths retain their revision IDs. The merge adds no schema changes;
Alembic runs the missing branch before reaching this single successor.
Future migrations must extend this one head.
"""

revision = "b8c7d6e5f403"
down_revision = ("a97470898855", "a3f1c7e9d2b4")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Join the histories without rewriting either published predecessor."""


def downgrade() -> None:
    """Separate the histories without changing application data."""
