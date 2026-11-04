"""Filling in what a game in a library is missing, without a full reimport.

Only ever adds: a blank field, an art file that does not exist, a time not yet
known. Anything already there, edited or locked is left alone, so running this
again can never undo someone's work. A game checked with nothing more to find
waits RECHECK_SECONDS before it is asked about again, so one with no entry on
any site does not cost requests on every run."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import select

from src.api.routes.settings import (
    get_or_create_app_integration_settings,
    get_or_create_scan_settings,
)
from src.core.integrations import resolve_integrations
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.game_matches import find_matches
from src.features.metadata.games import steam
from src.features.metadata.games.search import _steam_result
from src.features.metadata.games.time_to_beat import TimesLookup, fill_times
from src.helpers.game_art_download import fill_art, wanted_art

logger = logging.getLogger(__name__)

RECHECK_SECONDS = 30 * 24 * 60 * 60
# about one store page a second, the pace Steam tolerates
GAP_SECONDS = 1.0
_PLACEHOLDER = "Steam app "
_MAX_TITLE = 500
_BLANK_FIELDS = (
    ("description", "save_description"),
    ("developer", "save_developer"),
    ("publisher", "save_publisher"),
    ("age_rating", "save_age_rating"),
    ("tags", "save_tags"),
    ("features", "save_features"),
)

_busy: set[UUID] = set()


@dataclass
class RepairResult:
    checked: int = 0
    names: int = 0
    art: int = 0
    times: int = 0
    failed: int = 0
    # still to be tried on a later run because a site did not answer
    hltb_error: str | None = None


def _steam_app_id(game: Game) -> int | None:
    external_id = game.external_id or ""
    return int(external_id) if game.source == "Steam" and external_id.isdigit() else None


def _has_placeholder_name(game: Game) -> bool:
    return game.title.startswith(_PLACEHOLDER) and "title" not in (game.locked_fields or [])


def needs_repair(game: Game, scan_settings: Any, now: int) -> bool:
    if _has_placeholder_name(game):
        return True
    if game.details_checked_at is not None and now - game.details_checked_at < RECHECK_SECONDS:
        return False
    wants_times = (
        scan_settings.save_time_to_beat
        and game.time_to_beat_hours is None
        and "time_to_beat_hours" not in (game.locked_fields or [])
    )
    return wants_times or bool(wanted_art(game, scan_settings))


def _apply_store_details(game: Game, details: dict[str, Any], scan_settings: Any) -> bool:
    """Fills blanks from the store page. Returns whether a placeholder name was
    replaced."""
    locked = game.locked_fields or []
    named = False
    if _has_placeholder_name(game) and details.get("name"):
        game.title = str(details["name"])[:_MAX_TITLE]
        game.sort_title = game.title.lower()
        named = True
    match = _steam_result({"id": int(game.external_id or 0)}, details)
    for field, setting in _BLANK_FIELDS:
        if field not in locked and not getattr(game, field) and getattr(scan_settings, setting):
            value = match.get(field)
            if value:
                setattr(game, field, value)
    if (
        game.release_date is None
        and "release_date" not in locked
        and scan_settings.save_release_date
        and match.get("release_date")
    ):
        try:
            game.release_date = date.fromisoformat(match["release_date"])
        except ValueError:
            pass
    return named


async def repair_game(
    game: Game,
    api_key: str | None,
    scan_settings: Any,
    lookup: TimesLookup,
    result: RepairResult,
) -> None:
    app_id = _steam_app_id(game)
    details = None
    answered = True
    if app_id and (_has_placeholder_name(game) or not game.description or not game.developer):
        try:
            details = await asyncio.to_thread(steam.get_app_details, app_id)
        except Exception:  # best-effort, the art and times below still run
            logger.warning("Steam store details for app %s failed", app_id, exc_info=True)
            answered = False
    if details and _apply_store_details(game, details, scan_settings):
        result.names += 1

    kinds = wanted_art(game, scan_settings)
    if kinds:
        saved = await fill_art(
            game.id,
            kinds,
            app_id,
            None if game.title.startswith(_PLACEHOLDER) else game.title,
            api_key,
            (details or {}).get("header_image"),
        )
        result.art += len(saved)

    if scan_settings.save_time_to_beat and not game.title.startswith(_PLACEHOLDER):
        if await fill_times(game, lookup):
            result.times += 1

    # a site that did not answer says nothing about the game, so it is asked again
    if answered and lookup.hltb_error is None:
        game.details_checked_at = int(time.time())
    result.checked += 1


async def repair_user_games(
    user_id: UUID, on_progress: Callable[[int, int], None] | None = None
) -> RepairResult:
    """Goes through one person's library a game at a time; one that fails is
    left as it is and does not stop the others."""
    result = RepairResult()
    if user_id in _busy:
        return result
    _busy.add(user_id)
    try:
        async with SessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None:
                return result
            api_key = user.steamgriddb_api_key
            scan_settings = await get_or_create_scan_settings(user_id, db)
            integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
            now = int(time.time())
            games = await db.scalars(
                select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None))
            )
            game_ids = [g.id for g in games.all() if needs_repair(g, scan_settings, now)]
            await db.commit()

        lookup = TimesLookup(integrations.igdb_client_id, integrations.igdb_client_secret)
        for position, game_id in enumerate(game_ids):
            if on_progress:
                on_progress(position, len(game_ids))
            try:
                async with SessionLocal() as db:
                    game = await db.get(Game, game_id)
                    # it may have been removed while this was running
                    if game is None or game.deleted_at is not None:
                        continue
                    scan_settings = await get_or_create_scan_settings(user_id, db)
                    await repair_game(game, api_key, scan_settings, lookup, result)
                    await db.commit()
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


async def repair_all_games() -> dict[str, Any]:
    async with SessionLocal() as db:
        user_ids = list(await db.scalars(select(User.id).where(User.is_active.is_(True))))
    total = RepairResult()
    for user_id in user_ids:
        one = await repair_user_games(user_id)
        total.checked += one.checked
        total.names += one.names
        total.art += one.art
        total.times += one.times
        total.failed += one.failed
        total.hltb_error = total.hltb_error or one.hltb_error
    return asdict(total)
