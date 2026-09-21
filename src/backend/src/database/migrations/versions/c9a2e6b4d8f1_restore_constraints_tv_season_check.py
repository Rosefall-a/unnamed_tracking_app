"""restore what the squashed baseline dropped, and track the TV season check

The baseline migration was generated from the models, which never listed a
few database-level rules the old history had created: one row per episode
number in a season, the card archive-number uniqueness, and several
indexes. A database that came from the old history still has all of them;
one built fresh from the baseline had none. Everything here is created only
if it is missing, so it is safe on both.

Also adds tv_shows.seasons_checked_at, when TVmaze was last asked whether a
show has seasons we do not have.

Revision ID: c9a2e6b4d8f1
Revises: f6bb4f914739
Create Date: 2026-09-19
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c9a2e6b4d8f1"
down_revision: Union[str, None] = "f6bb4f914739"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_EPISODE_TABLES = ("anime_episodes", "tv_episodes")


def upgrade() -> None:
    op.execute("ALTER TABLE tv_shows ADD COLUMN IF NOT EXISTS seasons_checked_at BIGINT")

    for table in _EPISODE_TABLES:
        # a fresh database can have duplicate episode numbers if a sync ever
        # raced; keep the row with the most progress and drop the rest, or
        # the constraint below could not be created
        op.execute(
            f"""
            DELETE FROM {table} WHERE id IN (
                SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                        PARTITION BY season_id, episode_number
                        ORDER BY watched DESC, (note IS NOT NULL) DESC, (rating IS NOT NULL) DESC, id
                    ) AS rn FROM {table}
                ) ranked WHERE rn > 1
            )
            """
        )
        name = f"uq_{table}_season_id_episode_number"
        op.execute(
            f"""
            DO $$ BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
                    ALTER TABLE {table} ADD CONSTRAINT {name} UNIQUE (season_id, episode_number);
                END IF;
            END $$;
            """
        )
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_season_watched ON {table} (season_id, watched)")
        op.execute(f"CREATE INDEX IF NOT EXISTS ix_{table}_air_at ON {table} (air_at) WHERE air_at IS NOT NULL")

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_cards_archive_number_user_active "
        "ON cards (user_id, archive_number) WHERE archive_number IS NOT NULL"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_games_parent_game_id ON games (parent_game_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_games_parent_game_id")
    op.execute("DROP INDEX IF EXISTS ix_cards_archive_number_user_active")
    for table in _EPISODE_TABLES:
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_air_at")
        op.execute(f"DROP INDEX IF EXISTS ix_{table}_season_watched")
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS uq_{table}_season_id_episode_number")
    op.execute("ALTER TABLE tv_shows DROP COLUMN IF EXISTS seasons_checked_at")
