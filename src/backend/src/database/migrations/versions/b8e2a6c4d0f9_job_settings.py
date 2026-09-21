"""how each cleanup job is scheduled

Created only if missing, so it is safe on a database that already has it
(see docs/migrations.md).

Revision ID: b8e2a6c4d0f9
Revises: a7d1f5b9c3e8
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b8e2a6c4d0f9"
down_revision: Union[str, None] = "a7d1f5b9c3e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS job_settings (
            job_id VARCHAR(50) PRIMARY KEY,
            enabled BOOLEAN NOT NULL DEFAULT false,
            interval_hours INTEGER NOT NULL DEFAULT 24,
            last_run_at BIGINT,
            last_result JSONB,
            updated_at BIGINT NOT NULL
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS job_settings")
