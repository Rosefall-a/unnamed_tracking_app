"""Filling in what a game in a library is missing, without a full reimport.

Only ever adds: a blank field, an art file that does not exist, a time not yet
known. Anything already there, edited or locked is left alone, so running this
again can never undo someone's work. A game checked with nothing more to find
waits RECHECK_SECONDS before it is asked about again, so one with no entry on
any site does not cost requests on every run, unless the run is forced.

Moving a placeholder folder and writing a game's info file need no site, so
every run does those for the whole library."""

from __future__ import annotations

import asyncio
import logging
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, cast
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.library_sync import (
    _add_to_series_collection,
    _fetch_series_from_igdb,
    _normalize_title,
)
from src.api.routes.settings import (
    get_or_create_app_integration_settings,
    get_or_create_scan_settings,
)
from src.core.integrations import Integrations, resolve_integrations
from src.database.models.game import Game
from src.database.models.media_item import MediaItem
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.game_matches import find_matches
from src.features.metadata.games import steam
from src.features.metadata.games.search import _steam_result, search_game_metadata
from src.features.metadata.games.time_to_beat import TimesLookup, fill_times
from src.helpers.game_art_download import fill_art, replace_poor_cover, wanted_art
from src.helpers.game_info_file import has_info_file, write_game_info
from src.helpers.library_games import (
    PLACEHOLDER_TITLE,
    has_placeholder_folder,
    name_folder_after_title,
)
from src.helpers.media import MediaKind, media_subdir
from src.helpers.save_game_asset import DATA_ROOT

logger = logging.getLogger(__name__)

RECHECK_SECONDS = 30 * 24 * 60 * 60
# about one store page a second, the pace Steam tolerates
GAP_SECONDS = 1.0
_MAX_TITLE = 500
# age rating and series are left out of what makes a game need repair: most
# games have none, so they are only filled while a game is being looked at
_DETAIL_FIELDS = (
    ("description", "save_description"),
    ("developer", "save_developer"),
    ("publisher", "save_publisher"),
    ("tags", "save_tags"),
    ("features", "save_features"),
    ("release_date", "save_release_date"),
)
_OPTIONAL_FIELDS = (("age_rating", "save_age_rating"),)
_SEARCH_SETTINGS = (
    "provider_order",
    "image_provider_order",
    *(setting for _, setting in _DETAIL_FIELDS),
    "save_age_rating",
    "save_series",
    "save_time_to_beat",
)

_busy: set[UUID] = set()


@dataclass
class RepairResult:
    checked: int = 0
    names: int = 0
    details: int = 0
    art: int = 0
    covers: int = 0
    times: int = 0
    folders: int = 0
    info_files: int = 0
    failed: int = 0
    # still to be tried on a later run because a site did not answer
    hltb_error: str | None = None

    def add(self, other: RepairResult) -> None:
        for name in (
            "checked",
            "names",
            "details",
            "art",
            "covers",
            "times",
            "folders",
            "info_files",
            "failed",
        ):
            setattr(self, name, getattr(self, name) + getattr(other, name))
        self.hltb_error = self.hltb_error or other.hltb_error


def _steam_app_id(game: Game) -> int | None:
    external_id = game.external_id or ""
    return int(external_id) if game.source == "Steam" and external_id.isdigit() else None


def _has_placeholder_name(game: Game) -> bool:
    return game.title.startswith(PLACEHOLDER_TITLE) and "title" not in (game.locked_fields or [])


def _is_blank(game: Game, field: str) -> bool:
    value = getattr(game, field)
    if field == "tags":
        # a synced game starts with only the name of where it came from
        return not set(value or []) - {game.source}
    return not value


def blank_details(game: Game, scan_settings: Any) -> list[str]:
    locked = game.locked_fields or []
    return [
        field
        for field, setting in _DETAIL_FIELDS
        if field not in locked and getattr(scan_settings, setting) and _is_blank(game, field)
    ]


def _wants_times(game: Game, scan_settings: Any) -> bool:
    return (
        scan_settings.save_time_to_beat
        and game.time_to_beat_hours is None
        and "time_to_beat_hours" not in (game.locked_fields or [])
    )


def needs_repair(game: Game, scan_settings: Any, now: int, force: bool = False) -> bool:
    if _has_placeholder_name(game):
        return True
    recently_checked = (
        game.details_checked_at is not None and now - game.details_checked_at < RECHECK_SECONDS
    )
    if recently_checked and not force:
        return False
    return (
        _wants_times(game, scan_settings)
        or bool(wanted_art(game, scan_settings))
        or bool(blank_details(game, scan_settings))
    )


def _set_blanks(game: Game, match: dict[str, Any], scan_settings: Any) -> bool:
    """Fills blanks from a store page or search result. Returns whether it filled any."""
    locked = game.locked_fields or []
    filled = False
    for field, setting in (*_DETAIL_FIELDS, *_OPTIONAL_FIELDS):
        if field in locked or not getattr(scan_settings, setting) or not _is_blank(game, field):
            continue
        value = match.get(field)
        if not value:
            continue
        if field == "release_date":
            try:
                value = date.fromisoformat(value)
            except ValueError:
                continue
        elif field == "tags" and game.source:
            value = [*value, game.source] if game.source not in value else value
        setattr(game, field, value)
        filled = True
    return filled


def _apply_store_details(
    game: Game, details: dict[str, Any], scan_settings: Any
) -> tuple[bool, bool]:
    """Returns whether a placeholder name was replaced and whether a blank was filled."""
    named = False
    if _has_placeholder_name(game) and details.get("name"):
        game.title = str(details["name"])[:_MAX_TITLE]
        game.sort_title = game.title.lower()
        named = True
    match = _steam_result({"id": int(game.external_id or 0)}, details)
    return named, _set_blanks(game, match, scan_settings)


async def _details_from_search(
    game: Game, user: User, scan_settings: Any, integrations: Integrations
) -> bool:
    """A game not from Steam has no store id, so its details come from a search,
    and only an entry with exactly its name counts."""
    preferences = {name: getattr(scan_settings, name) for name in _SEARCH_SETTINGS}
    response = await asyncio.to_thread(
        search_game_metadata,
        game.title,
        5,
        user.steamgriddb_api_key,
        preferences,
        user,
        integrations.igdb_client_id,
        integrations.igdb_client_secret,
        include_image_providers=False,
        only_matching=True,
    )
    target = _normalize_title(game.title)
    match = next(
        (
            r
            for r in response.get("results") or []
            if _normalize_title(r.get("title") or "") == target
        ),
        None,
    )
    return _set_blanks(game, match, scan_settings) if match else False


async def _fill_series(game: Game, scan_settings: Any, integrations: Integrations) -> None:
    if game.series or "series" in (game.locked_fields or []) or not scan_settings.save_series:
        return
    series = await _fetch_series_from_igdb(
        game.title, integrations.igdb_client_id, integrations.igdb_client_secret
    )
    if series:
        game.series = series
        _add_to_series_collection(game, series)


async def repair_game(
    game: Game,
    user: User,
    scan_settings: Any,
    lookup: TimesLookup,
    integrations: Integrations,
    result: RepairResult,
) -> None:
    app_id = _steam_app_id(game)
    details = None
    answered = True
    missing = blank_details(game, scan_settings)
    if app_id and (_has_placeholder_name(game) or missing or not game.age_rating):
        try:
            details = await asyncio.to_thread(steam.get_app_details, app_id)
        except Exception:  # best-effort, the art and times below still run
            logger.warning("Steam store details for app %s failed", app_id, exc_info=True)
            answered = False
    filled = False
    if details:
        named, filled = _apply_store_details(game, details, scan_settings)
        result.names += named
    elif not app_id and missing and not game.title.startswith(PLACEHOLDER_TITLE):
        try:
            filled = await _details_from_search(game, user, scan_settings, integrations)
        except Exception:
            logger.warning("Looking up the details of %s failed", game.id, exc_info=True)
            answered = False
    result.details += filled

    named_now = not game.title.startswith(PLACEHOLDER_TITLE)
    if named_now:
        await _fill_series(game, scan_settings, integrations)

    kinds = wanted_art(game, scan_settings)
    if kinds:
        saved = await fill_art(
            game.id,
            kinds,
            app_id,
            game.title if named_now else None,
            user.steamgriddb_api_key,
            (details or {}).get("header_image"),
            (integrations.igdb_client_id, integrations.igdb_client_secret),
        )
        result.art += len(saved)

    if scan_settings.save_time_to_beat and named_now:
        if await fill_times(game, lookup):
            result.times += 1

    # a site that did not answer says nothing about the game, so it is asked again
    if answered and lookup.hltb_error is None:
        game.details_checked_at = int(time.time())
    result.checked += 1


async def _repair_one(
    game_id: UUID,
    user_id: UUID,
    lookup: TimesLookup,
    integrations: Integrations,
    result: RepairResult,
) -> None:
    async with SessionLocal() as db:
        game = await db.get(Game, game_id)
        user = await db.get(User, user_id)
        # it may have been removed while this was running
        if game is None or user is None or game.deleted_at is not None:
            return
        scan_settings = await get_or_create_scan_settings(user_id, db)
        await repair_game(game, user, scan_settings, lookup, integrations, result)
        await db.commit()
        result.folders += await name_folder_after_title(db, game)
        # every run already wrote one per game: this one has what was just found
        write_game_info(game)


async def repair_user_games(
    user_id: UUID,
    on_progress: Callable[[int, int], None] | None = None,
    force: bool = False,
) -> RepairResult:
    """Goes through one person's library a game at a time; one that fails is
    left as it is and does not stop the others."""
    result = RepairResult()
    if user_id in _busy:
        return result
    _busy.add(user_id)
    try:
        async with SessionLocal() as db:
            if await db.get(User, user_id) is None:
                return result
            scan_settings = await get_or_create_scan_settings(user_id, db)
            integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
            now = int(time.time())
            games = (
                await db.scalars(
                    select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None))
                )
            ).all()
            game_ids = [g.id for g in games if needs_repair(g, scan_settings, now, force)]
            for game in games:
                result.folders += await name_folder_after_title(db, game)
                result.info_files += write_game_info(game)
            await db.commit()

        lookup = TimesLookup(integrations.igdb_client_id, integrations.igdb_client_secret)
        for position, game_id in enumerate(game_ids):
            if on_progress:
                on_progress(position, len(game_ids))
            try:
                await _repair_one(game_id, user_id, lookup, integrations, result)
            except Exception:
                logger.exception("Filling in game %s failed", game_id)
                result.failed += 1
            await asyncio.sleep(GAP_SECONDS)

        result.hltb_error = lookup.hltb_error
        if result.names:
            # a game can only be recognised as one added by hand once it has its name
            async with SessionLocal() as db:
                await find_matches(db, user_id)
                await db.commit()
    finally:
        _busy.discard(user_id)
    return result


async def _better_cover(
    db: AsyncSession, game: Game, user: User, integrations: Integrations
) -> bool:
    app_id = _steam_app_id(game)
    if not app_id or game.title.startswith(PLACEHOLDER_TITLE):
        return False
    scan_settings = await get_or_create_scan_settings(game.user_id, db)
    if not scan_settings.save_key_art:
        return False
    return await replace_poor_cover(
        game,
        app_id,
        game.title,
        user.steamgriddb_api_key,
        (integrations.igdb_client_id, integrations.igdb_client_secret),
    )


async def replace_poor_covers(
    user_id: UUID, on_progress: Callable[[int, int], None] | None = None
) -> RepairResult:
    """Goes through one person's Steam games for covers that are only Steam's old
    small copy or its generated image. Asks Steam about every game, so it only runs
    when someone asks for it, never on a schedule."""
    result = RepairResult()
    if user_id in _busy:
        return result
    _busy.add(user_id)
    try:
        async with SessionLocal() as db:
            integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
            games = await _user_games(db, user_id)
            game_ids = [g.id for g in games if _steam_app_id(g)]
            await db.commit()
        for position, game_id in enumerate(game_ids):
            if on_progress:
                on_progress(position, len(game_ids))
            try:
                async with SessionLocal() as db:
                    game = await db.get(Game, game_id)
                    user = await db.get(User, user_id)
                    if game is None or user is None or game.deleted_at is not None:
                        continue
                    result.covers += await _better_cover(db, game, user, integrations)
                    await db.commit()
                    result.checked += 1
            except Exception:
                logger.exception("Replacing the cover of game %s failed", game_id)
                result.failed += 1
            await asyncio.sleep(GAP_SECONDS)
    finally:
        _busy.discard(user_id)
    return result


async def replace_all_poor_covers(
    on_progress: Callable[[str, int, int], None] | None = None,
) -> dict[str, Any]:
    async with SessionLocal() as db:
        users = (
            await db.execute(select(User.id, User.username).where(User.is_active.is_(True)))
        ).all()
    total = RepairResult()

    def reporter(username: str) -> Callable[[int, int], None] | None:
        if on_progress is None:
            return None
        return lambda done, count: on_progress(username, done, count)

    for user_id, username in users:
        total.add(await replace_poor_covers(user_id, reporter(username)))
    return asdict(total)


async def repair_single_game(game_id: UUID) -> RepairResult | None:
    """One game, whatever its last check said. None if there is no such game."""
    result = RepairResult()
    async with SessionLocal() as db:
        game = await db.get(Game, game_id)
        if game is None or game.deleted_at is not None:
            return None
        user_id = game.user_id
        integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
        await db.commit()
    lookup = TimesLookup(integrations.igdb_client_id, integrations.igdb_client_secret)
    await _repair_one(game_id, user_id, lookup, integrations, result)
    result.hltb_error = lookup.hltb_error
    async with SessionLocal() as db:
        game = await db.get(Game, game_id)
        user = await db.get(User, user_id)
        if game is not None and user is not None:
            result.covers += await _better_cover(db, game, user, integrations)
        await db.commit()
    return result


async def repair_all_games(
    on_progress: Callable[[str, int, int], None] | None = None, force: bool = False
) -> dict[str, Any]:
    async with SessionLocal() as db:
        users = (
            await db.execute(select(User.id, User.username).where(User.is_active.is_(True)))
        ).all()
    total = RepairResult()

    def reporter(username: str) -> Callable[[int, int], None] | None:
        if on_progress is None:
            return None
        return lambda done, count: on_progress(username, done, count)

    for user_id, username in users:
        total.add(await repair_user_games(user_id, reporter(username), force))
    return asdict(total)


# What the repair screen counts. Each says what a game is missing, in words the
# screen can look up; the ones after "unfixable" are reported but never changed.
def _problems(game: Game, scan_settings: Any, missing_media: int) -> list[str]:
    found = []
    if _has_placeholder_name(game):
        found.append("placeholder_name")
    if has_placeholder_folder(game):
        found.append("placeholder_folder")
    found.extend(f"no_{kind}" for kind in wanted_art(game, scan_settings))
    found.extend(f"no_{field}" for field in blank_details(game, scan_settings))
    if _wants_times(game, scan_settings):
        found.append("no_times")
    if not has_info_file(game):
        found.append("no_info_file")
    if missing_media:
        found.append("missing_media")
    return found


def _media_is_gone(game: Game, kind: MediaKind, filename: str) -> bool:
    folder = DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    return not (folder / media_subdir(kind) / Path(filename).name).is_file()


async def _missing_media(db: AsyncSession, games: list[Game]) -> Counter[UUID]:
    by_id = {g.id: g for g in games}
    rows = await db.execute(
        select(MediaItem.game_id, MediaItem.kind, MediaItem.filename).where(
            MediaItem.game_id.in_(by_id), MediaItem.deleted_at.is_(None)
        )
    )
    return Counter(
        game_id
        for game_id, kind, name in rows.all()
        if _media_is_gone(by_id[game_id], cast(MediaKind, kind), name)
    )


async def _user_games(db: AsyncSession, user_id: UUID) -> list[Game]:
    rows = await db.scalars(select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None)))
    return list(rows.all())


async def scan_libraries() -> list[dict[str, Any]]:
    """Read only: what each person's library is missing, game by game added up."""
    now = int(time.time())
    people = []
    async with SessionLocal() as db:
        users = (await db.execute(select(User.id, User.username).order_by(User.username))).all()
        for user_id, username in users:
            games = await _user_games(db, user_id)
            if not games:
                continue
            scan_settings = await get_or_create_scan_settings(user_id, db)
            missing = await _missing_media(db, games)
            counts: Counter[str] = Counter()
            for game in games:
                counts.update(_problems(game, scan_settings, missing[game.id]))
            people.append(
                {
                    "user_id": str(user_id),
                    "username": username,
                    "games": len(games),
                    "problems": dict(counts),
                    "to_fix": sum(needs_repair(g, scan_settings, now) for g in games),
                    "to_fix_forced": sum(needs_repair(g, scan_settings, now, True) for g in games),
                }
            )
        await db.commit()
    return people


async def games_with_problem(user_id: UUID, problem: str, limit: int = 500) -> list[dict[str, Any]]:
    async with SessionLocal() as db:
        games = await _user_games(db, user_id)
        scan_settings = await get_or_create_scan_settings(user_id, db)
        missing = await _missing_media(db, games)
        rows = [
            {
                "id": str(g.id),
                "title": g.title,
                "source": g.source,
                "folder": g.folder_location,
                "checked_at": g.details_checked_at,
            }
            for g in sorted(games, key=lambda g: g.sort_title)
            if problem in _problems(g, scan_settings, missing[g.id])
        ]
        await db.commit()
    return rows[:limit]
