"""A game's history as the library already knows it: the day it was last
played, finished and bought, and how many achievements were unlocked on each
day, with their names. Nothing here is logged separately or guessed; it is
read from the game and its achievements, so it goes back as far as that data
does (an achievement unlocked in 2014 shows on its day in 2014).

Shared by the calendar (api/routes/media_extras.py, behind its own display
switches) and the History tab, which always shows all of it.

Days are UTC days, the same as the calendar has always used.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import aggregate_order_by
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.achievement import Achievement
from src.database.models.game import Game

# names shown with a day's achievements; the count always covers all of them
ACHIEVEMENT_NAMES_SHOWN = 3


def _day(stamp: int) -> str:
    return datetime.fromtimestamp(stamp, tz=timezone.utc).date().isoformat()


def _entry(kind: str, game_id: UUID, title: str, day: str, count: int = 1) -> dict[str, Any]:
    return {
        "kind": kind,
        "game_id": game_id,
        "title": title,
        "date": day,
        "count": count,
        "poster_url": f"/api/game/{game_id}/assets/key_art",
    }


async def game_history(db: AsyncSession, user_id: UUID, since: int = 0) -> list[dict[str, Any]]:
    """Played, finished and bought days, and achievements per game per day, from
    `since` (unix seconds) on, oldest first."""
    entries: list[dict[str, Any]] = []
    games = (
        await db.scalars(select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None)))
    ).all()
    for game in games:
        for kind, stamp in (
            ("game_played", game.last_played_at),
            ("game_finished", game.completion_date),
            ("game_purchased", game.purchase_date),
        ):
            if stamp is not None and stamp >= since:
                entries.append(_entry(kind, game.id, game.title, _day(stamp)))

    day = func.date(func.timezone("UTC", func.to_timestamp(Achievement.unlocked_at)))
    rows = (
        await db.execute(
            select(
                Game.id,
                Game.title,
                day,
                func.count(),
                func.array_agg(aggregate_order_by(Achievement.name, Achievement.unlocked_at)),
            )
            .join(Game, Game.id == Achievement.game_id)
            .where(
                Game.user_id == user_id,
                Game.deleted_at.is_(None),
                Achievement.unlocked.is_(True),
                Achievement.unlocked_at.isnot(None),
                Achievement.unlocked_at >= since,
            )
            .group_by(Game.id, Game.title, day)
        )
    ).all()
    for game_id, title, unlocked_day, count, names in rows:
        entry = _entry("game_achievements", game_id, title, unlocked_day.isoformat(), count)
        entry["names"] = [n for n in (names or []) if n][:ACHIEVEMENT_NAMES_SHOWN]
        entries.append(entry)
    entries.sort(key=lambda e: e["date"])
    return entries
