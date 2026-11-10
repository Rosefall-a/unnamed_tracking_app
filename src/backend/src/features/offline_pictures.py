"""Keeping a local copy of every picture a library shows, so it can be viewed
with no internet. Game art is already saved with the game. Posters, backdrops,
achievement icons, episode stills and the pictures and clips in game
descriptions are fetched when a row is saved (helpers/image_prefetch.py),
but a row saved before that existed, or while a site did not answer, only has the
address. This finds those and fetches them, and only ever adds files."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.database.models.achievement import Achievement
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.game import Game
from src.database.models.movies import Movie
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow
from src.database.session import SessionLocal
from src.helpers import image_prefetch, local_copies
from src.helpers.remote_images import (
    RemoteImageError,
    cache_path,
    fetch_and_store,
    fetch_icon,
    icon_cache_path,
)

_KINDS: tuple[tuple[Any, str], ...] = ((Movie, "movie"), (TVShow, "tv"), (Anime, "anime"))
# a few at a time, so a big library does not hammer TMDB, AniList or Steam
_PARALLEL = 6


def _online(url: str | None) -> bool:
    # a bare folder (Steam's way of saying there is no icon) has nothing to save
    return bool(url) and str(url).startswith(("http://", "https://")) and not str(url).endswith("/")


Missing = tuple[str, Path, Callable[[str, Path], None]]


def _resized(width: int) -> Callable[[str, Path], None]:
    return lambda url, target: fetch_and_store(url, target, width)


async def _missing(user_id: UUID) -> dict[str, list[Missing]]:
    """(address, local file, how to fetch it) for everything with no local copy."""
    found: dict[str, list[Missing]] = {kind: [] for _, kind in _KINDS}
    found["icon"] = []
    found["still"] = []
    found["page"] = []
    cache = image_prefetch.MEDIA_ROOT / str(user_id) / ".cache"
    async with SessionLocal() as db:
        for model, kind in _KINDS:
            for row in (await db.execute(select(model).where(model.user_id == user_id))).scalars():
                for name, url in image_prefetch.media_image_names(row):
                    if not _online(url):
                        continue
                    target = cache_path(cache, kind, str(row.id), name, url)
                    if not target.is_file():
                        found[kind].append((url, target, _resized(image_prefetch.WIDTHS[name])))
        icons = (
            await db.execute(
                select(Achievement.icon_url)
                .join(Game, Game.id == Achievement.game_id)
                .where(Game.user_id == user_id, Achievement.icon_url.is_not(None))
                .distinct()
            )
        ).scalars()
        for icon in icons:
            if icon is None or not _online(icon):
                continue
            target = icon_cache_path(image_prefetch.ICON_ROOT, icon)
            if not target.is_file():
                found["icon"].append((icon, target, fetch_icon))
        for episode, season, show in (
            (TVEpisode, TVSeason, TVShow),
            (AnimeEpisode, AnimeSeason, Anime),
        ):
            stills = (
                await db.execute(
                    select(episode.still_url)
                    .join(season, season.id == episode.season_id)
                    .join(show, show.id == season.show_id)
                    .where(show.user_id == user_id, episode.still_url.is_not(None))
                )
            ).scalars()
            for still in stills:
                if still is None or not _online(still):
                    continue
                target = local_copies.still_path(cache, still)
                if not target.is_file():
                    found["still"].append((still, target, local_copies.fetch_still))
        descriptions = (
            await db.execute(
                select(Game.description).where(
                    Game.user_id == user_id, Game.description.is_not(None)
                )
            )
        ).scalars()
        queued: set[Path] = set()
        for description in descriptions:
            for url in local_copies.description_files(description):
                target = local_copies.description_file_path(cache, url)
                if target not in queued and not target.is_file():
                    queued.add(target)
                    found["page"].append((url, target, local_copies.fetch_description_file))
    return found


async def count_missing(user_id: UUID) -> dict[str, int]:
    return {kind: len(items) for kind, items in (await _missing(user_id)).items()}


def _fetch(url: str, target: Path, fetch: Callable[[str, Path], None]) -> None:
    fetch(url, target)


async def save_missing(
    user_id: UUID, progress: Callable[[int, int], None] | None = None
) -> dict[str, int]:
    """Fetches every missing picture. One that fails is counted and left for the
    next run; nothing already saved is touched."""
    todo = [item for items in (await _missing(user_id)).values() for item in items]
    lane = asyncio.Semaphore(_PARALLEL)
    result = {"checked": len(todo), "pictures": 0, "failed": 0}
    done = 0

    async def one(url: str, target: Path, fetch: Callable[[str, Path], None]) -> None:
        nonlocal done
        async with lane:
            try:
                await asyncio.to_thread(_fetch, url, target, fetch)
                result["pictures"] += 1
            except (RemoteImageError, OSError):
                result["failed"] += 1
            done += 1
            if progress:
                progress(done, len(todo))

    if progress:
        progress(0, len(todo))
    await asyncio.gather(*(one(*item) for item in todo))
    return result
