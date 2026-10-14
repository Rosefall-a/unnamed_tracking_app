"""Entries that may be the same game, and folding one into the other.

A game added by hand (or from IGDB, GOG...) and the same game later brought in by a
Steam sync end up as two entries. Nothing is merged on its own: a pair is recorded,
the person decides, and the decision can be undone while the Steam entry is still in
the trash.

A merge always keeps the entry the person made. It owns their notes, screenshots and
files, which live in its folder, so nothing on disk has to move. What it takes from
the Steam entry is the Steam identity (so later syncs land on it), the achievements,
the playtime, and any details it was missing.
"""

import re
import time
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameLink
from src.database.models.game_match import GameMatch
from src.database.models.notification import Notification

_NOISE = re.compile(r"[™®©'’]")
_NON_WORD = re.compile(r"[^a-z0-9]+")

# details the Steam entry can lend: set on the original when it has none, or in
# place of the original's when the person says Steam's are better
_DETAIL_FIELDS = (
    "description",
    "developer",
    "publisher",
    "series",
    "release_date",
    "age_rating",
    "time_to_beat_hours",
    "tags",
    "features",
)


def match_key(title: str) -> str:
    """Titles that differ only in case, punctuation, an apostrophe or a trademark mark
    compare equal."""
    return _NON_WORD.sub(" ", _NOISE.sub("", title).lower()).strip()


def _same_year(a: date | None, b: date | None) -> bool:
    """Two different games can share a name (Prey 2006 and Prey 2017): when both
    release years are known they must agree."""
    return a is None or b is None or a.year == b.year


async def find_matches(db: AsyncSession, user_id: UUID) -> int:
    """Record every pair that looks like one game: a Steam entry with a Steam id and
    an entry from anywhere else that has no id of its own and the same title.
    Pairs already known (decided or not) are left alone. Returns how many are new."""
    games = list(
        (
            await db.scalars(
                select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None))
            )
        ).all()
    )
    steam = [g for g in games if g.source == "Steam" and g.external_id]
    others = [g for g in games if g.source != "Steam" and not g.external_id]
    if not steam or not others:
        return 0
    known = {
        (m.original_id, m.steam_id)
        for m in (await db.scalars(select(GameMatch).where(GameMatch.user_id == user_id))).all()
    }
    by_title: dict[str, list[Game]] = {}
    for game in others:
        by_title.setdefault(match_key(game.title), []).append(game)

    created = 0
    for steam_game in steam:
        for original in by_title.get(match_key(steam_game.title), []):
            if (original.id, steam_game.id) in known:
                continue
            if not _same_year(original.release_date, steam_game.release_date):
                continue
            match = GameMatch(user_id=user_id, original_id=original.id, steam_id=steam_game.id)
            db.add(match)
            await db.flush()
            db.add(_notification(user_id, match, original, steam_game))
            known.add((original.id, steam_game.id))
            created += 1
    return created


def _notification(user_id: UUID, match: GameMatch, original: Game, steam_game: Game) -> Notification:
    return Notification(
        user_id=user_id,
        kind="possible_duplicate",
        # the Steam entry is the one a person will find in their library
        media_type="game",
        media_id=steam_game.id,
        title=steam_game.title,
        body=f"This may be the same game as “{original.title}”. Merge them or keep both.",
        poster_url=None,
        event_at=int(time.time()),
        dedupe_key=f"game-match:{match.id}",
    )


def _snapshot(original: Game) -> dict[str, Any]:
    return {
        "source": original.source,
        "external_id": original.external_id,
        "playtime_seconds": original.playtime_seconds,
        "last_played_at": original.last_played_at,
        "stale_since": original.stale_since,
        "details": {
            field: _jsonable(getattr(original, field)) for field in _DETAIL_FIELDS
        },
        "links": [link.id for link in original.links],
    }


def _jsonable(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "__float__") and not isinstance(value, int | float | bool):
        return float(value)
    return value


def _from_json(field: str, value: Any) -> Any:
    if field == "release_date" and isinstance(value, str):
        return date.fromisoformat(value)
    return value


async def merge(db: AsyncSession, match: GameMatch, prefer: str) -> None:
    """Fold the Steam entry into the original. `prefer` says whose details win where
    both have one: "mine" keeps the original's, "steam" takes Steam's."""
    original = await db.get(Game, match.original_id)
    steam_game = await db.get(Game, match.steam_id)
    if original is None or steam_game is None or original.deleted_at or steam_game.deleted_at:
        raise ValueError("One of the two games is no longer in the library.")

    undo = _snapshot(original)

    # the details, never past a field the person locked
    locked = set(original.locked_fields or [])
    for field in _DETAIL_FIELDS:
        theirs = getattr(steam_game, field)
        if field in locked or not theirs:
            continue
        if prefer == "steam" or not getattr(original, field):
            setattr(original, field, theirs)

    # the Steam identity, so the next sync lands on this entry
    original.source = "Steam"
    original.external_id = steam_game.external_id
    original.playtime_seconds = max(original.playtime_seconds or 0, steam_game.playtime_seconds or 0)
    if steam_game.last_played_at:
        original.last_played_at = max(original.last_played_at or 0, steam_game.last_played_at)
    original.stale_since = None

    have = {link.url for link in original.links}
    for link in steam_game.links:
        if link.url not in have:
            original.links.append(GameLink(label=link.label, url=link.url))

    # achievements move across; one the original already has is not duplicated
    owned = {
        (a.provider, a.external_id)
        for a in (await db.scalars(select(Achievement).where(Achievement.game_id == original.id))).all()
    }
    moved: list[str] = []
    for achievement in (
        await db.scalars(select(Achievement).where(Achievement.game_id == steam_game.id))
    ).all():
        if (achievement.provider, achievement.external_id) in owned:
            continue
        achievement.game_id = original.id
        moved.append(str(achievement.id))
    undo["moved_achievements"] = moved

    steam_game.deleted_at = int(time.time())
    match.status = "merged"
    match.prefer = prefer
    match.undo = undo
    match.resolved_at = int(time.time())


async def undo_merge(db: AsyncSession, match: GameMatch) -> None:
    """Put the original back as it was and bring the Steam entry back out of the trash."""
    original = await db.get(Game, match.original_id)
    steam_game = await db.get(Game, match.steam_id)
    if original is None or steam_game is None or not match.undo:
        raise ValueError("This merge can no longer be undone.")
    undo = match.undo

    original.source = undo["source"]
    original.external_id = undo["external_id"]
    original.playtime_seconds = undo["playtime_seconds"]
    original.last_played_at = undo["last_played_at"]
    original.stale_since = undo["stale_since"]
    for field, value in undo["details"].items():
        setattr(original, field, _from_json(field, value))
    keep_links = set(undo["links"])
    original.links = [link for link in original.links if link.id in keep_links]

    ids = [UUID(i) for i in undo.get("moved_achievements", [])]
    if ids:
        await db.execute(update(Achievement).where(Achievement.id.in_(ids)).values(game_id=steam_game.id))

    steam_game.deleted_at = None
    match.status = "pending"
    match.prefer = None
    match.undo = None
    match.resolved_at = None


def keep_both(match: GameMatch) -> None:
    match.status = "kept_both"
    match.resolved_at = int(time.time())
