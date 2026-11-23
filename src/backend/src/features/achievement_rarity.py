"""How rare each Steam achievement is: the share of all players who have it.
Steam gives this out without a key. Older imports never asked for it, so Repair
can fill it in; a fill only ever adds numbers, it never clears one, and it reads
nothing about the player."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy import func, select

from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.session import SessionLocal
from src.features.metadata.games import steam


def _missing_query(user_id: UUID) -> Any:
    return (
        select(Game.id, Game.external_id)
        .join(Achievement, Achievement.game_id == Game.id)
        .where(
            Game.user_id == user_id,
            Game.deleted_at.is_(None),
            Achievement.provider == "Steam",
            Achievement.global_percent.is_(None),
        )
        .group_by(Game.id, Game.external_id)
    )


async def count_missing_rarity(user_id: UUID) -> int:
    """Steam games with at least one achievement whose rarity is unknown."""
    async with SessionLocal() as db:
        return (
            await db.scalar(select(func.count()).select_from(_missing_query(user_id).subquery()))
        ) or 0


def apply_rarity(achievements: list[Achievement], percentages: dict[str, float]) -> int:
    """Puts each known percentage on its achievement. One Steam did not list
    keeps what it had."""
    changed = 0
    for achievement in achievements:
        value = percentages.get(str(achievement.external_id))
        if value is not None and achievement.global_percent != value:
            achievement.global_percent = value
            changed += 1
    return changed


async def fill_missing_rarity(
    user_id: UUID, progress: Callable[[int, int], None]
) -> dict[str, int]:
    """Asks Steam once per game that has achievements with no rarity."""
    async with SessionLocal() as db:
        games = (await db.execute(_missing_query(user_id))).all()
    filled = unanswered = 0
    progress(0, len(games))
    for done, (game_id, app_id) in enumerate(games, start=1):
        percentages = (
            await asyncio.to_thread(steam.get_global_percentages, int(app_id))
            if str(app_id or "").isdigit()
            else {}
        )
        if not percentages:
            unanswered += 1
        else:
            async with SessionLocal() as db:
                rows = (
                    await db.execute(
                        select(Achievement).where(
                            Achievement.game_id == game_id, Achievement.provider == "Steam"
                        )
                    )
                ).scalars().all()
                filled += apply_rarity(list(rows), percentages)
                await db.commit()
        progress(done, len(games))
    # games Steam gave no numbers for (it lists none, or did not answer)
    return {"rarity": filled, "no_rarity": unanswered}
