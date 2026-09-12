"""merge per-user API key migration heads

Revision ID: 20260911_merge_api_key_heads
Revises: 7a1f4c9d8e21, b4e91c2a7f08
Create Date: 2026-09-11

"""

from typing import Sequence, Union

revision: str = "20260911_merge_api_key_heads"
down_revision: Union[str, tuple[str, str], None] = (
    "7a1f4c9d8e21",
    "b4e91c2a7f08",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
