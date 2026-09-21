"""job schedules in minutes

The airing check runs every few minutes, so a job's interval is stored in
minutes instead of hours. Existing rows keep their schedule (hours times 60).
Safe to run again or on a database that already changed (see docs/migrations.md).

Revision ID: d4b7f2a9c1e5
Revises: c2a9e5d1f7b4
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op

revision: str = "d4b7f2a9c1e5"
down_revision: Union[str, None] = "c2a9e5d1f7b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE job_settings ADD COLUMN IF NOT EXISTS interval_minutes INTEGER NOT NULL DEFAULT 1440")
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'job_settings' AND column_name = 'interval_hours'
            ) THEN
                UPDATE job_settings SET interval_minutes = interval_hours * 60;
                ALTER TABLE job_settings DROP COLUMN interval_hours;
            END IF;
        END $$
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE job_settings ADD COLUMN IF NOT EXISTS interval_hours INTEGER NOT NULL DEFAULT 24")
    op.execute("UPDATE job_settings SET interval_hours = GREATEST(1, interval_minutes / 60)")
    op.execute("ALTER TABLE job_settings DROP COLUMN IF EXISTS interval_minutes")
