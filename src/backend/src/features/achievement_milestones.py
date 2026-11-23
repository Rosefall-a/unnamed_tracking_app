"""Achievement milestones worked out from the unlocks themselves: the 100th
achievement, the 10th perfect game, the first unlock rarer than 1%, and so on.
Nothing is stored; each one carries the exact moment it was reached, taken from
the provider's unlock times. A milestone whose moment cannot be known (an unlock
with no time) is still listed as reached, with no date, rather than guessed."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.achievement import Achievement
from src.database.models.game import Game

UNLOCK_STEPS = (1, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000)
PERFECT_STEPS = (1, 5, 10, 25, 50, 100, 250, 500, 1000)
# first unlock rarer than this share of players
RARITY_STEPS = (10.0, 5.0, 1.0, 0.5)


@dataclass
class Milestone:
    """One milestone reached; `at` is None when its moment cannot be known."""

    id: str
    kind: str
    label: str
    at: int | None
    game_id: str | None = None
    game_title: str | None = None
    achievement: str | None = None


@dataclass
class _Unlock:
    at: int | None
    game_id: UUID
    title: str
    name: str
    percent: float | None


def _ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n:,}{suffix}"


def _percent_text(value: float) -> str:
    return f"{value:g}%"


async def _rows(db: AsyncSession, user_id: UUID) -> list[Any]:
    return list(
        (
            await db.execute(
                select(
                    Achievement.game_id,
                    Game.title,
                    Achievement.name,
                    Achievement.unlocked,
                    Achievement.unlocked_at,
                    Achievement.global_percent,
                )
                .join(Game, Game.id == Achievement.game_id)
                .where(Game.user_id == user_id, Game.deleted_at.is_(None))
            )
        ).all()
    )


def _nth(items: list[_Unlock], n: int) -> _Unlock | None:
    """The unlock that made the count reach n, when every unlock has a time.
    With any undated unlock the order is not known, so there is no answer."""
    if any(u.at is None for u in items):
        return None
    return sorted(items, key=lambda u: (u.at or 0, u.name or ""))[n - 1]


def _split(rows: list[Any]) -> tuple[list[_Unlock], list[_Unlock]]:
    """Every unlock, and every perfect game as the unlock that finished it.
    A perfect game is reached when its last achievement unlocks."""
    unlocks: list[_Unlock] = []
    per_game: dict[UUID, list[Any]] = {}
    for row in rows:
        per_game.setdefault(row.game_id, []).append(row)
        if row.unlocked:
            unlocks.append(
                _Unlock(row.unlocked_at or None, row.game_id, row.title, row.name, row.global_percent)
            )
    perfect: list[_Unlock] = []
    for game_id, items in per_game.items():
        if all(i.unlocked for i in items):
            # unlocks in the same second: the same one is picked every time
            last = max(items, key=lambda i: (i.unlocked_at or 0, i.name or ""))
            dated = all(i.unlocked_at for i in items)
            perfect.append(
                _Unlock(last.unlocked_at if dated else None, game_id, last.title, last.name, None)
            )
    return unlocks, perfect


def _from(hit: _Unlock | None, milestone_id: str, kind: str, label: str) -> Milestone:
    return Milestone(
        milestone_id,
        kind,
        label,
        hit.at if hit else None,
        str(hit.game_id) if hit else None,
        hit.title if hit else None,
        hit.name if hit else None,
    )


def _counted(kind: str, steps: tuple[int, ...], items: list[_Unlock], word: str) -> list[Milestone]:
    return [
        _from(
            _nth(items, n),
            f"{kind}:{n}",
            kind,
            f"Your first {word}" if n == 1 else f"Your {_ordinal(n)} {word}",
        )
        for n in steps
        if len(items) >= n
    ]


def _rarest_firsts(unlocks: list[_Unlock]) -> list[Milestone]:
    """The first unlock under each rarity line. One unlock that was first under
    several lines counts once, for the rarest of them."""
    found: list[Milestone] = []
    used: list[_Unlock] = []
    for limit in sorted(RARITY_STEPS):
        rare = [u for u in unlocks if u.percent is not None and u.percent < limit]
        if not rare:
            continue
        first = None
        if all(u.at is not None for u in rare):
            first = min(rare, key=lambda u: (u.at or 0, u.name or ""))
            if any(first is u for u in used):
                continue
            used.append(first)
        milestone = _from(
            first, f"rarity:{limit:g}", "rarity", f"First achievement rarer than {_percent_text(limit)}"
        )
        if first:
            milestone.achievement = f"{first.name} ({_percent_text(first.percent or 0)})"
        found.append(milestone)
    return found


def build(rows: list[Any]) -> dict[str, Any]:
    """Every milestone reached, newest first (undated last), and the next
    unlock and perfect-game milestone with how far along it is."""
    unlocks, perfect = _split(rows)
    reached = (
        _counted("unlocks", UNLOCK_STEPS, unlocks, "achievement")
        + _counted("perfect", PERFECT_STEPS, perfect, "perfect game")
        + _rarest_firsts(unlocks)
    )
    reached.sort(key=lambda m: (m.at is None, -(m.at or 0)))
    upcoming = []
    for kind, steps, count, word in (
        ("unlocks", UNLOCK_STEPS, len(unlocks), "achievement"),
        ("perfect", PERFECT_STEPS, len(perfect), "perfect game"),
    ):
        target = next((n for n in steps if n > count), None)
        if target is not None:
            upcoming.append(
                {
                    "kind": kind,
                    "label": f"Your {_ordinal(target)} {word}",
                    "current": count,
                    "target": target,
                }
            )
    return {
        "reached": [asdict(m) for m in reached],
        "next": upcoming,
        "totals": {"unlocked": len(unlocks), "perfect": len(perfect)},
    }


async def milestones_for(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    """The milestones for one person's library."""
    return build(await _rows(db, user_id))


async def unlock_times(db: AsyncSession, user_id: UUID) -> dict[str, Any]:
    """Every unlock time and every moment a game became perfect, for goals
    counted over a year or a month in the person's own time. Totals include
    unlocks with no time, which only an all-time count can use."""
    unlocks, perfect = _split(await _rows(db, user_id))
    return {
        "unlocks": sorted(u.at for u in unlocks if u.at),
        "perfect": sorted(p.at for p in perfect if p.at),
        "totals": {"unlocked": len(unlocks), "perfect": len(perfect)},
    }
