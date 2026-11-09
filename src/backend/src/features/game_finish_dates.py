"""When a game was really finished. A sync that sees every achievement unlocked
marks it Mastered, and the status change stamps the day of the sync, so a game
finished in 2022 and imported today read as finished today. The last unlock is
the real date.

Games also gain achievements after they are mastered (an update or DLC). Every
sync saves achievements before it changes the status, so an achievement first
seen after the Mastered date was added later and says nothing about when the
game was finished. Only the ones that existed on that date are looked at."""

from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameStatus
from src.database.models.game_field_change import GameFieldChange


def true_finish_date(completion: int | None, achievements: list[Achievement]) -> int | None:
    """The day the set the game had when it was marked Mastered was finished, or
    None when that cannot be told exactly (so the saved date stays)."""
    if completion is None:
        # no date at all: only a set that is finished right now gives one
        if not achievements or not all(a.unlocked and a.unlocked_at for a in achievements):
            return None
        return max(a.unlocked_at for a in achievements if a.unlocked_at)
    existed = [a for a in achievements if a.created_at <= completion]
    if not existed:
        # nothing was saved before the date: it was typed, set by hand or already fixed
        return None
    for a in existed:
        if not a.unlocked or a.unlocked_at is None or a.unlocked_at > completion:
            # still locked on the day it was marked Mastered, so it was set by hand
            return None
    last = max(a.unlocked_at for a in existed if a.unlocked_at)
    return last if last < completion else None


async def correct_finish_dates(db: AsyncSession, user_id: UUID) -> int:
    """Moves a Mastered game's date back to the day its achievements were really
    finished. A date someone typed in is left alone, and so is any game where that
    day cannot be told exactly. Returns how many changed; the caller commits."""
    typed_in = select(GameFieldChange.game_id).where(
        GameFieldChange.field_name == "completion_date"
    )
    games = (
        (
            await db.execute(
                select(Game).where(
                    Game.user_id == user_id,
                    Game.deleted_at.is_(None),
                    Game.status == GameStatus.MASTERED,
                    Game.id.not_in(typed_in),
                )
            )
        )
        .scalars()
        .all()
    )
    if not games:
        return 0
    by_game: dict[UUID, list[Achievement]] = defaultdict(list)
    for achievement in (
        await db.execute(select(Achievement).where(Achievement.game_id.in_([g.id for g in games])))
    ).scalars():
        by_game[achievement.game_id].append(achievement)
    changed = 0
    for game in games:
        day = true_finish_date(game.completion_date, by_game[game.id])
        if day is not None and day != game.completion_date:
            game.completion_date = day
            changed += 1
    return changed
