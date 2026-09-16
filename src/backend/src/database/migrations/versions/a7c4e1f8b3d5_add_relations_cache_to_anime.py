"""add relations cache to anime

Revision ID: a7c4e1f8b3d5
Revises: f3a8c751d2e4
Create Date: 2026-09-16

Adds `anime.relations_cache`/`relations_cached_at` — the Related tab's
chain/branches/recommendations payload, stored after the first AniList
fetch instead of re-fetched on every visit. AniList's public rate limit
is low and a single Related-tab load already means a dozen+ requests (one
per prequel/sequel chain hop, one per branch-group reorder lookup), so
repeat visits hitting AniList every time was the main source of 429s.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a7c4e1f8b3d5"
down_revision: Union[str, None] = "f3a8c751d2e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "anime", sa.Column("relations_cache", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        "anime", sa.Column("relations_cached_at", sa.BigInteger(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("anime", "relations_cached_at")
    op.drop_column("anime", "relations_cache")
