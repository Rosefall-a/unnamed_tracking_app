"""Mastered games get the day of their last achievement unlock as their finish date.

A sync that saw every achievement unlocked stamped the day of the sync instead, so a
game finished in 2022 and imported later read as finished on the import day. Only a
date later than the real one is moved, never one typed in by hand, and achievements
added to a game after it was mastered are not counted. Imports
and the repair tools keep it right from here on (features/game_finish_dates.py).

Revision ID: d8f2b6a4e1c3
Revises: c5e9a1d3f7b2
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "d8f2b6a4e1c3"
down_revision: str | None = "c5e9a1d3f7b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Only achievements first seen on or before the Mastered date count: one added to
# the game later (an update, DLC) says nothing about when it was finished. Every
# sync saves achievements before it changes the status, so the ones that existed
# then all have created_at at or before it.
FIX_FINISH_DATES = (
    """
        UPDATE games AS g
        SET completion_date = sets.last_unlock
        FROM (
            SELECT
                g2.id AS game_id,
                count(*) FILTER (WHERE a.created_at <= g2.completion_date) AS existed,
                count(*) FILTER (
                    WHERE a.created_at <= g2.completion_date
                      AND (NOT a.unlocked OR a.unlocked_at IS NULL
                           OR a.unlocked_at > g2.completion_date)
                ) AS still_locked,
                max(a.unlocked_at) FILTER (
                    WHERE a.created_at <= g2.completion_date AND a.unlocked
                ) AS last_unlock
            FROM games AS g2
            JOIN achievements AS a ON a.game_id = g2.id
            WHERE g2.status = 'MASTERED' AND g2.completion_date IS NOT NULL
            GROUP BY g2.id
        ) AS sets
        WHERE sets.game_id = g.id
          AND sets.existed > 0
          AND sets.still_locked = 0
          AND sets.last_unlock IS NOT NULL
          AND g.completion_date > sets.last_unlock
          AND NOT EXISTS (
              SELECT 1 FROM game_field_changes AS f
              WHERE f.game_id = g.id AND f.field_name = 'completion_date'
          )
    """,
    """
        UPDATE games AS g
        SET completion_date = sets.last_unlock
        FROM (
            SELECT
                game_id,
                bool_and(unlocked AND unlocked_at IS NOT NULL) AS all_done,
                max(unlocked_at) AS last_unlock
            FROM achievements
            GROUP BY game_id
        ) AS sets
        WHERE sets.game_id = g.id
          AND g.status = 'MASTERED'
          AND g.completion_date IS NULL
          AND sets.all_done
          AND NOT EXISTS (
              SELECT 1 FROM game_field_changes AS f
              WHERE f.game_id = g.id AND f.field_name = 'completion_date'
          )
    """,
)


def upgrade() -> None:
    for statement in FIX_FINISH_DATES:
        op.execute(statement)


def downgrade() -> None:
    # the stamped import days were never the real dates, so there is nothing to restore
    pass
