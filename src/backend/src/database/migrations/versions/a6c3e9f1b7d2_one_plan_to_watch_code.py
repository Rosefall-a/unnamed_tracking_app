"""Plan to Watch is stored one way, and what the removed plugin manager left goes.

The app shows WISHLIST and WATCHLIST as the same Plan to Watch, and saves WISHLIST
when it is picked, but imports used to save WATCHLIST. Both now read WISHLIST, so
lists, filters and stats cannot count them apart. Nothing else about a title changes.

The reverted plugin manager left a job row and six tables behind. A table is only
dropped while it is empty; one that holds anything is kept as it is.

Revision ID: a6c3e9f1b7d2
Revises: f4b8d2e6a1c9
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

from src.database import migration_helpers as h

revision: str = "a6c3e9f1b7d2"
down_revision: str | None = "f4b8d2e6a1c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLAN_TABLES = ("movies", "tv_shows", "tv_seasons", "anime", "anime_seasons")
PLUGIN_TABLES = (
    "plugin_permission_audit",
    "plugin_permission_requests",
    "plugin_permission_grants",
    "plugin_notification_provider_registrations",
    "plugin_lifecycle_transactions",
    "plugin_client_identities",
)


def upgrade() -> None:
    for table in PLAN_TABLES:
        op.execute(f"UPDATE {table} SET status = 'WISHLIST' WHERE status = 'WATCHLIST'")
    op.execute("DELETE FROM job_settings WHERE job_id = 'plugin_updates'")
    conn = op.get_bind()
    for table in PLUGIN_TABLES:
        if not h.has_table(table):
            continue
        if conn.exec_driver_sql(f"SELECT EXISTS (SELECT 1 FROM {table})").scalar():
            continue
        op.execute(f"DROP TABLE {table}")


def downgrade() -> None:
    # which titles were saved as WATCHLIST is not kept, and both mean the same,
    # so they stay WISHLIST; the plugin tables belong to code that no longer exists
    pass
