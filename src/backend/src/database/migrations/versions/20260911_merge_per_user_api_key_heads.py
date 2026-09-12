"""merge deployment credential migration with the main migration head

Revision ID: 20260911_merge_api_key_heads
Revises: c1e7a4d9b2f6, a6c1e9f4b2d7
Create Date: 2026-09-11

The deployment-wide provider credential migration branched from an older
migration while the main migration chain continued through the game-folder
repair migration. Merge the two actual heads so ``alembic upgrade head`` has
one unambiguous target.
"""

from typing import Sequence, Union

revision: str = "20260911_merge_api_key_heads"
down_revision: Union[str, tuple[str, str], None] = (
    "c1e7a4d9b2f6",
    "a6c1e9f4b2d7",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
