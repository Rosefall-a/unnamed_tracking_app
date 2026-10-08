"""The slow parts of a Steam import, done a few games at a time.

The library sync itself (with `achievements=later`) only saves the owned games
and their playtime, which is one Steam request. Reading each game's
achievements takes two or three more, and each new game's store page, tags,
series and artwork about a second, so both happen here in small batches the app
asks for one after another: no single request runs long enough for a proxy to
time it out, and a game that fails is left as it is instead of failing the rest.
"""

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.library_sync import (
    _SYNC_CONCURRENCY,
    _add_source_tag_and_collection,
    _apply_status,
    _enrich_steam_game_by_appid,
    _get_or_create_game,
    _infer_status,
    _replace_achievements,
)
from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.preferences import load_preferences
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import steam, steam_wishlist
from src.features.metadata.games.steam_achievements import (
    SteamAchievementData,
    fetch_steam_achievements,
)
from src.helpers.steam_achievement_rows import steam_achievement_rows

router = APIRouter(
    prefix="/api/library-sync/steam",
    tags=["library-sync"],
    dependencies=[Depends(get_current_user)],
)

_PLACEHOLDER = "Steam app "


class EnrichRequest(BaseModel):
    game_ids: list[UUID] = Field(max_length=25)


class AchievementsRequest(BaseModel):
    """Up to 25 Steam games to read achievements for."""

    game_ids: list[UUID] = Field(max_length=25)
    # the sync set these games' status from playtime alone (they are new, or
    # just moved off the wishlist): settle it now the achievements are known
    status_game_ids: list[UUID] = Field(default_factory=list, max_length=25)


async def _steam_games(db: AsyncSession, user: User, ids: list[UUID]) -> list[Game]:
    return list(
        (
            await db.scalars(
                select(Game).where(
                    Game.id.in_(ids),
                    Game.user_id == user.id,
                    Game.source == "Steam",
                    Game.deleted_at.is_(None),
                )
            )
        ).all()
    )


@router.post("/achievements")
async def import_achievements(
    body: AchievementsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Read the achievements of up to 25 of the user's Steam games, as the
    library sync does with `achievements=now`."""
    if not current_user.steam_id or not current_user.steam_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Save your Steam ID and API key first."
        )
    api_key = current_user.steam_api_key
    try:
        steam_id = await asyncio.to_thread(steam.resolve_steam_id, current_user.steam_id, api_key)
    except steam.SteamLibraryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    games = await _steam_games(db, current_user, body.game_ids)
    semaphore = asyncio.Semaphore(_SYNC_CONCURRENCY)

    async def _fetch(game: Game) -> SteamAchievementData:
        if not (game.external_id or "").isdigit():
            return {}, [], None
        async with semaphore:
            return await fetch_steam_achievements(steam_id, api_key, int(game.external_id or ""))

    fetched = await asyncio.gather(*(_fetch(g) for g in games))
    settle = set(body.status_game_ids)
    synced = 0
    unavailable: list[str] = []
    for game, (schema, unlocked, descriptions) in zip(games, fetched):
        total = unlocked_count = 0
        if schema and unlocked is None:
            # Steam would not say what is unlocked: keep what is stored
            unavailable.append(game.title)
        elif schema and unlocked is not None:
            rows = steam_achievement_rows(schema, unlocked, None, descriptions)
            await _replace_achievements(db, game.id, "Steam", rows)
            synced += len(rows)
            total = len(rows)
            unlocked_count = sum(1 for r in rows if r["unlocked"])
        if game.id in settle:
            _apply_status(
                game,
                _infer_status(
                    playtime_seconds=game.playtime_seconds,
                    total_achievements=total,
                    unlocked_achievements=unlocked_count,
                ),
            )
    await db.commit()
    return {"achievements_synced": synced, "achievements_unavailable": unavailable}


@router.post("/wishlist")
async def import_wishlist(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Add the Steam wishlist as Wishlist games, when the setting is on. The
    names come later, from the same enrich step as every other new game."""
    if not (await load_preferences(db, current_user.id))["steam_import_wishlist"]:
        return {"enabled": False, "added": 0, "game_ids": []}
    if not current_user.steam_id or not current_user.steam_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Save your Steam ID and API key first."
        )
    try:
        steam_id = await asyncio.to_thread(
            steam.resolve_steam_id, current_user.steam_id, current_user.steam_api_key
        )
        app_ids = await asyncio.to_thread(
            steam_wishlist.get_wishlist_app_ids, steam_id, current_user.steam_api_key
        )
    except steam.SteamLibraryError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    game_ids: list[str] = []
    for app_id in app_ids:
        game, created = await _get_or_create_game(
            db, current_user.id, f"{_PLACEHOLDER}{app_id}", "Steam", external_id=str(app_id)
        )
        if created:
            game.status = GameStatus.WISHLIST
            _add_source_tag_and_collection(game, "Steam")
            await db.flush()
            game_ids.append(str(game.id))
    await db.commit()
    return {"enabled": True, "wishlisted": len(app_ids), "added": len(game_ids), "game_ids": game_ids}


@router.post("/enrich")
async def enrich_games(
    body: EnrichRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int]:
    """Fill in the store details, tags, series and artwork of up to 25 of the
    user's Steam games."""
    games = await _steam_games(db, current_user, body.game_ids)
    integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    use_tags = (await load_preferences(db, current_user.id))["steam_user_tags"]
    enriched = failed = 0
    for game in games:
        try:
            app_id = int(game.external_id or "")
            await _enrich_steam_game_by_appid(
                game,
                app_id,
                current_user,
                integrations.igdb_client_id,
                integrations.igdb_client_secret,
                use_tags,
            )
            enriched += 1
        except Exception:  # noqa: BLE001 - one game must not fail the others
            failed += 1
        await db.commit()
    return {"enriched": enriched, "failed": failed}

