"""Connecting an Epic Games account and importing its library.

Epic's library lists only ids (namespace, catalog item id, app name), so each
new game needs a catalog lookup for its title, details and artwork. An import
is therefore a series of short requests the app makes one after another: each
reads the library and playtime again (a few requests), updates the games
already imported, and adds the next few new ones, so none runs long enough for
a proxy to time it out. Epic has no achievements service open to this sign-in,
so none are imported.
"""

from __future__ import annotations

import asyncio
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.library_sync import (
    _MAX_TITLE,
    _SYNC_CONCURRENCY,
    _add_source_tag_and_collection,
    _add_to_series_collection,
    _apply_status,
    _fetch_series_from_igdb,
    _flag_stale_games,
    _get_or_create_game,
    _infer_status,
)
from src.api.routes.settings import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.crypto import decrypt_secret, encrypt_secret
from src.core.integrations import resolve_integrations
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import epic
from src.helpers.game_art_download import download_asset

router = APIRouter(
    prefix="/api/library-sync/epic",
    tags=["library-sync"],
    dependencies=[Depends(get_current_user)],
)

SOURCE = "Epic Games"
# new games added per request: each takes a catalog lookup, an IGDB series
# lookup and up to three artwork downloads (with their resized copies), which
# must stay well inside a proxy's 60 seconds
_NEW_PER_REQUEST = 8
# catalog lookups per request, counting entries that turn out to be DLC
_LOOKUPS_PER_REQUEST = 60

# the short-lived access token per user, so the requests of one import don't
# each trade the refresh token (Epic replaces it every time) for a new one
_SESSIONS: dict[UUID, epic.EpicSession] = {}


class EpicConnectRequest(BaseModel):
    """What was copied off Epic's code page (see epic.extract_authorization_code)."""

    code: str = Field(min_length=1, max_length=4000)


def _remember(user: User, session: epic.EpicSession) -> None:
    user.epic_refresh_token = encrypt_secret(session.refresh_token)
    user.epic_account_id = session.account_id
    user.epic_display_name = session.display_name or user.epic_display_name
    _SESSIONS[user.id] = session


def _forget(user: User) -> None:
    user.epic_refresh_token = None
    user.epic_account_id = None
    user.epic_display_name = None
    _SESSIONS.pop(user.id, None)


@router.get("/login-url")
async def login_url() -> dict[str, str]:
    """The epicgames.com page that signs in and shows the code to paste."""
    return {"url": epic.LOGIN_URL}


@router.post("/connect")
async def connect_epic(
    payload: EpicConnectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str | None]:
    """Sign in with the one-time code from Epic's page. Only the refresh token
    it is traded for is kept (encrypted), never the code or a password."""
    try:
        session = await asyncio.to_thread(epic.EpicClient().sign_in, payload.code)
    except epic.EpicError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    _remember(current_user, session)
    await db.commit()
    return {"status": "connected", "display_name": current_user.epic_display_name}


@router.delete("/connect")
async def disconnect_epic(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Forget the sign-in. Imported games stay in the library."""
    _forget(current_user)
    await db.commit()
    return {"status": "not_configured"}


async def _session(db: AsyncSession, user: User) -> epic.EpicSession:
    cached = _SESSIONS.get(user.id)
    if (
        cached
        and cached.account_id == user.epic_account_id
        and cached.expires_at > time.time() + 60
    ):
        return cached
    if not user.epic_refresh_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Connect your Epic Games account first."
        )
    try:
        refresh_token = decrypt_secret(user.epic_refresh_token)
    except RuntimeError as exc:  # saved under a SECRET_KEY that has since changed
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Connect Epic Games again."
        ) from exc
    # EpicError is a RuntimeError too, so it is caught here on its own: a sign-in
    # Epic refuses means connecting again, anything else (Epic down) is a 502
    try:
        session = await asyncio.to_thread(epic.EpicClient().refresh, refresh_token)
    except epic.EpicSignInExpired as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except epic.EpicError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    _remember(user, session)
    await db.commit()
    return session


def _apply_catalog(game: Game, item: dict) -> None:
    """A new game's details from its Epic catalog entry."""
    description = item.get("longDescription") or item.get("description")
    if description:
        game.description = description
    if item.get("developer"):
        game.developer = str(item["developer"])[:200]
    seller = (item.get("seller") or {}).get("name")
    if seller:
        game.publisher = str(seller)[:200]


@router.post("")
async def sync_epic_library(
    after: str | None = Query(default=None, max_length=64),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """One step of an Epic import: update every game already imported (its
    playtime, and clear a "missing from your library" flag), then add up to
    eight new ones, in catalog id order after `after`. While `next` comes
    back set, call again with `after=<next>`; the last step flags imported
    games that have left the library."""
    session = await _session(db, current_user)
    client = epic.EpicClient()
    try:
        records = await asyncio.to_thread(client.get_library_items, session.access_token)
        playtime = await asyncio.to_thread(
            client.get_playtime, session.access_token, session.account_id
        )
    except epic.EpicSignInExpired as exc:
        _SESSIONS.pop(current_user.id, None)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except epic.EpicError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    played = playtime or {}

    owned = {r["catalogItemId"]: r for r in records}
    existing = {
        g.external_id: g
        for g in (
            await db.scalars(
                select(Game).where(
                    Game.user_id == current_user.id,
                    Game.source == SOURCE,
                    Game.external_id.in_(list(owned)),
                    Game.deleted_at.is_(None),
                )
            )
        ).all()
    }
    for item_id, game in existing.items():
        game.stale_since = None
        seconds = played.get(owned[str(item_id)]["appName"])
        if seconds is not None:
            game.playtime_seconds = seconds

    pending = sorted(i for i in owned if i not in existing and (after is None or i > after))
    lookups = pending[:_LOOKUPS_PER_REQUEST]
    catalog = await asyncio.to_thread(
        client.get_catalog, session.access_token, [(owned[i]["namespace"], i) for i in lookups]
    )
    added: list[tuple[Game, dict]] = []
    # an Epic game added by hand before, now matched by its title
    matched: list[Game] = []
    skipped = 0
    last: str | None = None
    for item_id in lookups:
        last = item_id
        item = catalog.get(item_id)
        if not item or not item.get("title") or not epic.is_game(item):
            skipped += 1
            continue
        game, created = await _get_or_create_game(
            db, current_user.id, str(item["title"])[:_MAX_TITLE], SOURCE, external_id=item_id
        )
        seconds = played.get(owned[item_id]["appName"])
        if not created:
            # a game added by hand keeps its own playtime unless Epic has one
            if seconds is not None:
                game.playtime_seconds = seconds
            matched.append(game)
            continue
        game.playtime_seconds = seconds or 0
        _apply_catalog(game, item)
        _apply_status(game, _infer_status(playtime_seconds=game.playtime_seconds))
        _add_source_tag_and_collection(game, SOURCE)
        added.append((game, item))
        if len(added) >= _NEW_PER_REQUEST:
            break
    # the artwork is saved by looking the game up in its own session
    await db.commit()
    await _add_art_and_series(db, added)

    remaining = [i for i in pending if last is not None and i > last]
    flagged = 0
    if not remaining:
        touched = {g.id for g in [*existing.values(), *matched]} | {g.id for g, _ in added}
        flagged = await _flag_stale_games(db, current_user.id, SOURCE, touched)
        current_user.epic_library_synced_at = int(time.time())
    await db.commit()
    return {
        "games_added": len(added),
        "games_updated": len(existing) + len(matched),
        "achievements_synced": 0,
        "games_flagged_stale": flagged,
        "games": [g.title for g, _ in added],
        # library entries that are not games (DLC, add-ons) or have no catalog entry
        "skipped": skipped,
        # new library entries this step started with, and still left after it
        "pending": len(pending),
        "remaining": len(remaining),
        "next": last if remaining else None,
    }


async def _add_art_and_series(db: AsyncSession, added: list[tuple[Game, dict]]) -> None:
    """Artwork from the catalog and the series from IGDB, for new games.
    Best-effort: a picture that fails to download is just left out."""
    integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    semaphore = asyncio.Semaphore(_SYNC_CONCURRENCY)

    async def _one(game: Game, item: dict) -> None:
        async with semaphore:
            for kind, url in epic.art_urls(item).items():
                await download_asset(url, game.id, kind)
            series = await _fetch_series_from_igdb(
                game.title, integrations.igdb_client_id, integrations.igdb_client_secret
            )
            if series and not game.series:
                game.series = series
                _add_to_series_collection(game, series)

    await asyncio.gather(*(_one(g, i) for g, i in added))
