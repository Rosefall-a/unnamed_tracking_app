"""Downloading artwork as soon as it is saved, so no page waits on another site.

A movie, show or anime keeps the address of its poster and backdrop, and an
achievement the address of its icon. Whenever one of those rows is written
(added, imported, edited or refreshed from a metadata source) the picture is
fetched into this server's own cache in the background, using the same files
the image routes serve. A picture that could not be fetched is left for the
route to try again, and to redirect to the original if it still cannot.

Switched on by the app at startup; until then (tests, scripts) it does nothing.
"""

import asyncio
from pathlib import Path
from typing import Any

from sqlalchemy import event

from src.database.models.achievement import Achievement
from src.database.models.anime import Anime
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow
from src.helpers.remote_images import RemoteImageError, cache_path, fetch_and_store, icon_cache_path

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


async def _download(url: str, target: Path, width: int, lane: asyncio.Semaphore) -> None:
    try:
        async with lane:
            await asyncio.to_thread(fetch_and_store, url, target, width)
    except (RemoteImageError, OSError):
        _gave_up.add(target)
    finally:
        _running.discard(target)


def schedule(url: str | None, target: Path, width: int) -> None:
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
    task = loop.create_task(_download(url, target, width, lane))
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
