"""persist automatic restore notification timestamp"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260920_restore_notice"
down_revision: Union[str, Sequence[str], None] = "20260915_user_invitations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings",
        sa.Column("restore_notice_at", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.alter_column(
        "app_integration_settings",
        "restore_notice_at",
        server_default=None,
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "restore_notice_at")
