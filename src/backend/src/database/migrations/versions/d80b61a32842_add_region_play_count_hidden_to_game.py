"""add region, play_count, hidden to game

Revision ID: d80b61a32842
Revises: 48efa731484a
Create Date: 2026-09-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd80b61a32842'
down_revision: Union[str, None] = '48efa731484a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('games', sa.Column('region', sa.String(length=50), nullable=True))
    op.add_column(
        'games',
        sa.Column('play_count', sa.Integer(), nullable=False, server_default='0'),
    )
    op.add_column(
        'games',
        sa.Column('hidden', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('games', 'hidden')
    op.drop_column('games', 'play_count')
    op.drop_column('games', 'region')
