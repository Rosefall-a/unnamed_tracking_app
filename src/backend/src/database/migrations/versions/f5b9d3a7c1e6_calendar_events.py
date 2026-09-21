"""entries the user adds to the calendar by hand

Created only if missing, so it is safe on a database that already has it
(see docs/migrations.md).

Revision ID: f5b9d3a7c1e6
Revises: e4a8c2d6f1b3
Create Date: 2026-09-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f5b9d3a7c1e6"
down_revision: Union[str, None] = "e4a8c2d6f1b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS calendar_events (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(200) NOT NULL,
            event_date DATE NOT NULL,
            event_time VARCHAR(5),
            note TEXT,
            media_type VARCHAR(10),
            media_id UUID,
            created_at BIGINT NOT NULL,
            updated_at BIGINT NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_calendar_events_user_date ON calendar_events (user_id, event_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_calendar_events_user_date")
    op.execute("DROP TABLE IF EXISTS calendar_events")
