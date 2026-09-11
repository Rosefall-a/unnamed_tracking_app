"""add user_id and soft delete to movies

Revision ID: c2e5a9f4d817
Revises: a5f8c3e1b746
Create Date: 2026-09-11

The movies table has existed since f59d16fccd48 but was never wired up to
any real code — its model/schema/routes lived only on an old, never-merged
branch that predates multi-user auth entirely, with no user_id column and
no ownership scoping anywhere. This adds the same per-user + soft-delete
shape every other entity (Game, Card, Bounty) already has, as a hard
NOT NULL add since the table has never had working code writing to it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c2e5a9f4d817"
down_revision: Union[str, None] = "a5f8c3e1b746"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "movies",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    op.add_column("movies", sa.Column("deleted_at", sa.BigInteger(), nullable=True))
    op.create_index("ix_movies_user_id", "movies", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_movies_user_id", table_name="movies")
    op.drop_column("movies", "deleted_at")
    op.drop_column("movies", "user_id")
