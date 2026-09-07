"""create inbox_items

Revision ID: d4a6e9c2f731
Revises: c9f3a2d7e185
Create Date: 2026-09-05

Inbox media (bulk-uploaded, not yet assigned to a game) previously had no
DB row at all — just a bare file on disk, listed by walking the directory.
That meant no real upload date and no way to soft-delete it like every
other delete path in the app. This gives each inbox file a row: real
created_at, and deleted_at for the same 7-day trash pattern
game_archives already has.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "d4a6e9c2f731"
down_revision: Union[str, None] = "c9f3a2d7e185"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "inbox_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("filename", sa.String(length=500), nullable=False),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("deleted_at", sa.BigInteger(), nullable=True),
    )
    op.create_index("ix_inbox_items_user_id", "inbox_items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_inbox_items_user_id", table_name="inbox_items")
    op.drop_table("inbox_items")
