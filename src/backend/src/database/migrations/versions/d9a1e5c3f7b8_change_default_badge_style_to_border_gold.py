"""change default completion badge style/color to border/gold

Revision ID: d9a1e5c3f7b8
Revises: c8f4a2d6e9b3
Create Date: 2026-09-07

Also backfills any row still sitting at the old glow/platinum default — a
self-hosted app with no real installs beyond this one, so there's no
migration-safety reason to leave stale defaults in place.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d9a1e5c3f7b8"
down_revision: Union[str, None] = "c8f4a2d6e9b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("user_appearance_settings", "completion_badge_style", server_default="border")
    op.alter_column("user_appearance_settings", "completion_badge_color", server_default="#d4af37")
    op.execute(
        """
        UPDATE user_appearance_settings
        SET completion_badge_style = 'border', completion_badge_color = '#d4af37'
        WHERE completion_badge_style = 'glow' AND completion_badge_color = '#e5e4e2'
        """
    )


def downgrade() -> None:
    op.alter_column("user_appearance_settings", "completion_badge_style", server_default="glow")
    op.alter_column("user_appearance_settings", "completion_badge_color", server_default="#e5e4e2")
