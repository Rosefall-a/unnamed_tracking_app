"""create user_appearance_settings table

Revision ID: c8f4a2d6e9b3
Revises: b6e2c8a4d1f7
Create Date: 2026-09-06

Per-user cosmetic settings for how a 100%-complete (Mastered) game's card
is highlighted — style, color, placement, and an optional custom badge
image, replacing the earlier hardcoded 🏆 percent text.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c8f4a2d6e9b3"
down_revision: Union[str, None] = "b6e2c8a4d1f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_appearance_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("completion_badge_style", sa.String(length=20), nullable=False, server_default="glow"),
        sa.Column("completion_badge_color", sa.String(length=7), nullable=False, server_default="#e5e4e2"),
        sa.Column(
            "completion_badge_placement", sa.String(length=20), nullable=False, server_default="top-right"
        ),
        sa.Column("completion_badge_image_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("updated_at", sa.BigInteger(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("user_appearance_settings")
