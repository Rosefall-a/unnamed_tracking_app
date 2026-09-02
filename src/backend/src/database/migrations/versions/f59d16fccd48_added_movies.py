"""added movies

Revision ID: f59d16fccd48
Revises: 98357cb173a4
Create Date: 2026-09-02 05:20:30.841682

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f59d16fccd48'
down_revision: Union[str, None] = '98357cb173a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'movies',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('sort_title', sa.String(length=500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('release_date', sa.Date(), nullable=True),
        sa.Column('runtime_minutes', sa.Integer(), nullable=True),
        sa.Column('director', sa.String(length=200), nullable=True),
        sa.Column('writer', sa.String(length=200), nullable=True),
        sa.Column('studios', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('countries', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('languages', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('genres', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('tags', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('features', sa.ARRAY(sa.String()), nullable=False, server_default='{}'),
        sa.Column('age_rating', sa.String(length=20), nullable=True),
        sa.Column('tmdb_score', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True),
        sa.Column(
            'status',
            sa.Enum('DROPPED', 'WISHLIST', 'WATCHLIST', 'BACKLOG', 'IN_PROGRESS', 'WATCHED', 'FAVORITE', 'REWATCH', name='moviestatus', native_enum=False, length=30),
            nullable=False,
        ),
        sa.Column('priority', sa.String(length=20), nullable=True),
        sa.Column('favorite', sa.Boolean(), nullable=False),
        sa.Column('rewatches', sa.Integer(), nullable=False),
        sa.Column('rating_story', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_performance', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_soundtrack', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('rating_overall', sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column('personal_rank', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.BigInteger(), nullable=False),
        sa.Column('updated_at', sa.BigInteger(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('movies')