"""Downloading artwork as soon as it is saved, so no page waits on another site.

A movie, show or anime keeps the address of its poster and backdrop, an
achievement the address of its icon, an episode its still, and a game's
description the pictures and clips it shows. Whenever one of those rows is written
(added, imported, edited or refreshed from a metadata source) the picture is
fetched into this server's own cache in the background, using the same files
the image routes serve. A picture that could not be fetched is left for the
route to try again, and to redirect to the original if it still cannot.

Switched on by the app at startup; until then (tests, scripts) it does nothing.
"""

import asyncio
from collections.abc import Callable
from pathlib import Path
from typing import Any

from sqlalchemy import event, select

from src.database.models.achievement import Achievement
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.game import Game
from src.database.models.movies import Movie
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow
from src.helpers import local_copies
from src.helpers.remote_images import (
    RemoteImageError,
    cache_path,
    fetch_and_store,
    fetch_icon,
    icon_cache_path,
)

MEDIA_ROOT = Path("/data/users")
ICON_ROOT = Path("/data/cache")
# a poster shows at most about 200 px wide, a backdrop spans the page, an
# achievement icon is a small square
WIDTHS = {"poster": 400, "backdrop": 1920, "hero": 1920, "icon": 128}
# posters and backdrops are big files, icons are a few KB each and a game can
# have a hundred of them, so icons get a wider lane of their own
_PARALLEL = 4
_ICON_PARALLEL = 16

_semaphore: asyncio.Semaphore | None = None
_icon_semaphore: asyncio.Semaphore | None = None
_running: set[Path] = set()
_gave_up: set[Path] = set()
_tasks: set[asyncio.Task[None]] = set()


def enable() -> None:
    global _semaphore, _icon_semaphore
    _semaphore = asyncio.Semaphore(_PARALLEL)
    _icon_semaphore = asyncio.Semaphore(_ICON_PARALLEL)


async def _download(
    url: str,
    target: Path,
    width: int,
    lane: asyncio.Semaphore,
    fetch: Callable[[str, Path], None] | None,
) -> None:
    try:
        async with lane:
            if fetch is not None:
                await asyncio.to_thread(fetch, url, target)
            elif width == WIDTHS["icon"]:
                await asyncio.to_thread(fetch_icon, url, target)
            else:
                await asyncio.to_thread(fetch_and_store, url, target, width)
    except (RemoteImageError, OSError):
        _gave_up.add(target)
    finally:
        _running.discard(target)


def schedule(
    url: str | None,
    target: Path,
    width: int,
    fetch: Callable[[str, Path], None] | None = None,
) -> None:
    """Fetch `url` into `target` in the background unless it is already there.
    `fetch` saves it some other way than a resized picture (a clip, a still)."""
    lane = _icon_semaphore if width == WIDTHS["icon"] else _semaphore
    if not url or lane is None or target in _running or target in _gave_up:
        return
    if target.is_file():
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    _running.add(target)
    task = loop.create_task(_download(url, target, width, lane, fetch))
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


def media_image_names(row: Any) -> list[tuple[str, str]]:
    """(cache name, address) for each picture a title needs. A title with a
    backdrop uses it as its page hero too; one without uses the poster."""
    names = [("poster", row.poster_url)]
    names.append(("backdrop", row.backdrop_url) if row.backdrop_url else ("hero", row.poster_url))
    return [(name, url) for name, url in names if url]


def _media_saved(kind: str):
    def handler(_mapper: Any, _connection: Any, row: Any) -> None:
        cache = MEDIA_ROOT / str(row.user_id) / ".cache"
        for name, url in media_image_names(row):
            schedule(url, cache_path(cache, kind, str(row.id), name, url), WIDTHS[name])

    return handler


def _icon_saved(_mapper: Any, _connection: Any, row: Achievement) -> None:
    if row.icon_url and row.icon_url.startswith(("http://", "https://")):
        schedule(row.icon_url, icon_cache_path(ICON_ROOT, row.icon_url), WIDTHS["icon"])


for _model, _kind in ((Movie, "movie"), (TVShow, "tv"), (Anime, "anime")):
    event.listen(_model, "after_insert", _media_saved(_kind))
    event.listen(_model, "after_update", _media_saved(_kind))
event.listen(Achievement, "after_insert", _icon_saved)


def _description_saved(_mapper: Any, _connection: Any, row: Game) -> None:
    if not row.description or "http" not in row.description:
        return
    cache = local_copies.cache_root(MEDIA_ROOT, row.user_id)
    for url in local_copies.description_files(row.description):
        target = local_copies.description_file_path(cache, url)
        schedule(url, target, WIDTHS["backdrop"], local_copies.fetch_description_file)


# season id -> owner, so saving a season's worth of episodes asks once, not per episode
_season_owner: dict[Any, Any] = {}


def _still_saved(season_model: Any, show_model: Any):
    def handler(_mapper: Any, connection: Any, row: Any) -> None:
        url = row.still_url
        if not url or not url.startswith(("http://", "https://")) or _semaphore is None:
            return
        owner = _season_owner.get(row.season_id)
        if owner is None:
            owner = connection.execute(
                select(show_model.user_id)
                .join(season_model, season_model.show_id == show_model.id)
                .where(season_model.id == row.season_id)
            ).scalar()
            if owner is None:
                return
            if len(_season_owner) > 5000:
                _season_owner.clear()
            _season_owner[row.season_id] = owner
        target = local_copies.still_path(local_copies.cache_root(MEDIA_ROOT, owner), url)
        schedule(url, target, local_copies.STILL_WIDTH, local_copies.fetch_still)

    return handler


event.listen(Game, "after_insert", _description_saved)
event.listen(Game, "after_update", _description_saved)
for _episode, _season, _show in ((TVEpisode, TVSeason, TVShow), (AnimeEpisode, AnimeSeason, Anime)):
    event.listen(_episode, "after_insert", _still_saved(_season, _show))
    event.listen(_episode, "after_update", _still_saved(_season, _show))
