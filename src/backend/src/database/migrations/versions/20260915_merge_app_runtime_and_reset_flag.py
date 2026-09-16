"""merge the password-reset and app-runtime migration heads

Revision ID: 20260915_merge_app_runtime
Revises: 20260913_reset_flag, 20260914_app_runtime
"""

from typing import Sequence, Union

from alembic import op

revision: str = "20260915_merge_app_runtime"
down_revision: Union[str, Sequence[str], None] = (
    "20260913_reset_flag",
    "20260914_app_runtime",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
