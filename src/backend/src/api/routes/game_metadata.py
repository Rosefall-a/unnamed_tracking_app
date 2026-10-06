"""Game metadata routes, composed by the games router."""

import asyncio
import time
from uuid import UUID

import requests
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import (
    get_or_create_app_integration_settings,
    get_or_create_scan_settings,
)
from src.api.routes.utils.games import (
    _DATA_ROOT,
    _get_game_or_404,
    _record_field_changes,
    _scan_settings_to_preferences,
)
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.preferences import load_preferences
from src.core.titles import normalize_metadata_title as _normalize_metadata_title
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games.search import search_game_metadata
from src.helpers.save_game_asset import (
    ASSET_FILENAMES,
    save_game_asset,
)

_QUERY_DEFAULT = Query(..., min_length=2, max_length=100)


_LIMIT_DEFAULT = Query(default=8, ge=1, le=20)


_INCLUDE_IMAGES_DEFAULT = Query(default=True)


_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


router = APIRouter()
search_router = APIRouter()


class MetadataSearchResponse(BaseModel):
    __module__ = "src.api.routes.games"
    query: str
    providers: list[str]
    steamgriddb_configured: bool = False
    provider_errors: list[str] = []
    results: list[dict]


class MetadataRefreshRequest(BaseModel):
    __module__ = "src.api.routes.games"
    dry_run: bool = False
    update_text: bool = True
    fill_missing_art: bool = True
    overwrite_existing_art: bool = False
    expected_updated_at: int | None = None


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
@search_router.get("/metadata/search", response_model=MetadataSearchResponse)
async def search_metadata(
    query: str = _QUERY_DEFAULT,
    limit: int = _LIMIT_DEFAULT,
    include_images: bool = _INCLUDE_IMAGES_DEFAULT,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    """Search external providers for data that can prefill a new game.

    Keys come from the user's own settings first, then the server-wide ones
    (Server Integrations or the environment). Provider order and which
    fields get saved come from the user's scan settings.
    """
    scan_settings = await get_or_create_scan_settings(current_user.id, db)
    preferences = _scan_settings_to_preferences(scan_settings)
    preferences["steam_user_tags"] = (await load_preferences(db, current_user.id))[
        "steam_user_tags"
    ]
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    try:
        result = await asyncio.to_thread(
            search_game_metadata,
            query.strip(),
            limit,
            steamgriddb_api_key=current_user.steamgriddb_api_key,
            preferences=preferences,
            user=current_user,
            igdb_client_id=app_integrations.igdb_client_id,
            igdb_client_secret=app_integrations.igdb_client_secret,
            include_image_providers=include_images,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc

    if result.get("providers"):
        now = int(time.time())
        last_used = dict(scan_settings.provider_last_used)
        for provider_name in result["providers"]:
            last_used[provider_name] = now
        scan_settings.provider_last_used = last_used
        await db.commit()
    return result


# pylint: enable=duplicate-code


# Metadata updates and history tracking intentionally overlap in their declared fields.
# pylint: disable=duplicate-code
_GAME_METADATA_FIELDS = frozenset(
    {
        "title",
        "description",
        "developer",
        "publisher",
        "series",
        "tags",
        "features",
        "age_rating",
        "release_date",
        "time_to_beat_hours",
        "links",
    }
)
# pylint: enable=duplicate-code


def _metadata_value_is_present(value: object) -> bool:
    return value is not None and value != "" and value != []


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-branches,too-many-locals,too-many-statements
@router.post("/{game_id}/metadata/refresh")
async def refresh_game_metadata(
    game_id: UUID,
    payload: MetadataRefreshRequest,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    """Preview or apply a metadata-provider refresh for one game.

    Provider lookup uses the same configured game metadata registry as the
    existing search flow. Applying is server-side so authorization, locks,
    history, artwork protection, and stale-editor detection cannot be bypassed
    by a client replaying a provider result.
    """
    game = await _get_game_or_404(game_id, db, current_user.id)
    scan_settings = await get_or_create_scan_settings(current_user.id, db)
    preferences = _scan_settings_to_preferences(scan_settings)
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))

    try:
        result = await asyncio.to_thread(
            search_game_metadata,
            game.title,
            8,
            steamgriddb_api_key=current_user.steamgriddb_api_key,
            preferences=preferences,
            user=current_user,
            igdb_client_id=app_integrations.igdb_client_id,
            igdb_client_secret=app_integrations.igdb_client_secret,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc

    providers = result.get("providers", [])
    provider_errors = result.get("provider_errors", [])
    if providers:
        last_used = dict(scan_settings.provider_last_used)
        now = int(time.time())
        for provider_name in providers:
            last_used[provider_name] = now
        scan_settings.provider_last_used = last_used

    match = next(
        (
            candidate
            for candidate in result.get("results", [])
            if isinstance(candidate, dict)
            and _normalize_metadata_title(str(candidate.get("title") or ""))
            == _normalize_metadata_title(game.title)
        ),
        None,
    )
    if match is None:
        await db.commit()
        return {
            "status": "no-match",
            "provider": None,
            "provider_errors": provider_errors,
            "changed_fields": [],
            "skipped_locked_fields": [],
            "would_add_key_art": False,
            "would_add_banner": False,
            "game_updated_at": game.updated_at,
        }

    field_values: dict[str, object] = {
        "title": match.get("title"),
        "description": match.get("description"),
        "developer": match.get("developer"),
        "publisher": match.get("publisher"),
        "series": match.get("series"),
        "tags": match.get("tags"),
        "features": match.get("features"),
        "age_rating": match.get("age_rating"),
        "release_date": match.get("release_date"),
        "time_to_beat_hours": match.get("time_to_beat_hours"),
        "links": match.get("links"),
    }
    gated_flags = {
        "developer": "save_developer",
        "publisher": "save_publisher",
        "series": "save_series",
        "tags": "save_tags",
        "features": "save_features",
        "description": "save_description",
        "age_rating": "save_age_rating",
        "release_date": "save_release_date",
        "time_to_beat_hours": "save_time_to_beat",
    }
    updates: dict[str, object] = {}
    skipped_locked: list[str] = []
    for field, fresh in field_values.items():
        if (
            field != "title"
            and gated_flags.get(field)
            and not preferences.get(gated_flags[field], True)
        ):
            continue
        if not _metadata_value_is_present(fresh):
            continue
        if field in game.locked_fields:
            skipped_locked.append(field)
            continue
        current = getattr(game, field)
        if fresh != current:
            updates[field] = fresh

    changed_fields = sorted(updates)
    key_art_url = match.get("key_art_url")
    banner_url = match.get("banner_url")
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location
    key_art_exists = (game_dir / ASSET_FILENAMES["key_art"]).is_file()
    banner_exists = (game_dir / ASSET_FILENAMES["banner"]).is_file()
    would_add_key_art = bool(
        payload.fill_missing_art
        and key_art_url
        and (payload.overwrite_existing_art or not key_art_exists)
    )
    would_add_banner = bool(
        payload.fill_missing_art
        and banner_url
        and (payload.overwrite_existing_art or not banner_exists)
    )

    if payload.dry_run:
        # A preview records no game changes, but the existing provider-last-used
        # telemetry may be updated as part of the provider lookup.
        await db.commit()
        return {
            "status": "preview",
            "provider": match.get("provider"),
            "provider_errors": provider_errors,
            "changed_fields": changed_fields,
            "skipped_locked_fields": sorted(set(skipped_locked)),
            "would_add_key_art": would_add_key_art,
            "would_add_banner": would_add_banner,
            "game_updated_at": game.updated_at,
        }

    if payload.expected_updated_at is not None:
        # The preview may have been open while another tab or sync changed the game.
        # Re-read under a row lock before applying so two concurrent refreshes cannot
        # both pass the same stale timestamp.
        await db.rollback()
        locked_game = await db.scalar(
            select(Game)
            .where(Game.id == game_id, Game.user_id == current_user.id, Game.deleted_at.is_(None))
            .with_for_update()
        )
        if locked_game is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Game {game_id} not found"
            )
        if locked_game.updated_at != payload.expected_updated_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Game changed after the metadata preview. Refresh the editor and try again.",
            )
        game = locked_game
        # Recompute from the freshly locked row. Locks and configured save_* flags
        # may have changed while the preview was open, so do not trust preview data.
        updates = {}
        skipped_locked = []
        for field, fresh in field_values.items():
            if (
                field != "title"
                and gated_flags.get(field)
                and not preferences.get(gated_flags[field], True)
            ):
                continue
            if not _metadata_value_is_present(fresh):
                continue
            if field in game.locked_fields:
                skipped_locked.append(field)
                continue
            if getattr(game, field) != fresh:
                updates[field] = fresh
        changed_fields = sorted(updates)
        key_art_exists = (game_dir / ASSET_FILENAMES["key_art"]).is_file()
        banner_exists = (game_dir / ASSET_FILENAMES["banner"]).is_file()

    if payload.update_text:
        _record_field_changes(game, updates, db)
        for field, value in updates.items():
            setattr(game, field, value)

    if payload.fill_missing_art:

        async def _download_art(url: str) -> bytes:
            response = await asyncio.to_thread(requests.get, url, timeout=20)
            response.raise_for_status()
            return response.content

        if key_art_url and (payload.overwrite_existing_art or not key_art_exists):
            try:
                await save_game_asset(await _download_art(str(key_art_url)), game.id, "key_art")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                provider_errors.append(
                    f"{match.get('provider', 'Metadata')}: cover art could not be downloaded: {exc}"
                )
            else:
                would_add_key_art = True
        if banner_url and (payload.overwrite_existing_art or not banner_exists):
            try:
                await save_game_asset(await _download_art(str(banner_url)), game.id, "banner")
            except Exception as exc:  # pylint: disable=broad-exception-caught
                provider_errors.append(
                    f"{match.get('provider', 'Metadata')}: banner art could not be downloaded: {exc}"
                )
            else:
                would_add_banner = True

    await db.commit()
    await db.refresh(game)
    return {
        "status": "updated",
        "provider": match.get("provider"),
        "provider_errors": provider_errors,
        "changed_fields": changed_fields,
        "skipped_locked_fields": sorted(set(skipped_locked)),
        "would_add_key_art": would_add_key_art,
        "would_add_banner": would_add_banner,
        "game_updated_at": game.updated_at,
    }


# pylint: enable=too-many-branches,too-many-locals,too-many-statements
