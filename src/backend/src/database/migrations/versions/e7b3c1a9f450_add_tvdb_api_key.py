"""add tvdb_api_key to app_integration_settings

Revision ID: e7b3c1a9f450
Revises: d4a1e7c9f2b6
Create Date: 2026-09-14

TheTVDB v4 is the only real franchise/relations data source for TV shows
(TMDB has no collection concept for TV) — this adds its deployment-wide
API key alongside the existing tmdb/omdb keys, same Fernet-encrypted,
never-echoed-back treatment.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7b3c1a9f450"
down_revision: Union[str, None] = "d4a1e7c9f2b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "app_integration_settings", sa.Column("tvdb_api_key", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("app_integration_settings", "tvdb_api_key")
