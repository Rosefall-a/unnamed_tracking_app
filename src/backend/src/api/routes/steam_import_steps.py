"""The slow parts of a Steam import, done a few games at a time.

The library sync itself only saves the games and their achievements, which is
quick. Reading each new game's store page, tags, series and artwork takes about
a second per game, so it happens here in small batches the app asks for one
after another: no single request runs long enough to time out, and a game that
fails to enrich is left as it is instead of failing the rest.
"""

import asyncio
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.library_sync import (
    _add_source_tag_and_collection,
    _enrich_steam_game_by_appid,
    _get_or_create_game,
)
from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.preferences import load_preferences
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import steam, steam_wishlist

router = APIRouter(
    prefix="/api/library-sync/steam",
    tags=["library-sync"],
    dependencies=[Depends(get_current_user)],
)

_PLACEHOLDER = "Steam app "


class EnrichRequest(BaseModel):
    game_ids: list[UUID] = Field(max_length=25)


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
    games = (
        await db.scalars(
            select(Game).where(
                Game.id.in_(body.game_ids),
                Game.user_id == current_user.id,
                Game.source == "Steam",
                Game.deleted_at.is_(None),
            )
        )
    ).all()
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

