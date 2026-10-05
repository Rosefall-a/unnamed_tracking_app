"""API routes for managing games, notes, and game artwork."""

import asyncio
import re
import time
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse
from uuid import UUID

import requests
from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import Integer, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.settings import (
    get_or_create_app_integration_settings,
    get_or_create_scan_settings,
)
from src.api.schemas.game import (
    GameBulkUpdate,
    GameCreate,
    GameFieldChangeRead,
    GameRead,
    GameUpdate,
)
from src.core.app_integrations import get_max_upload_size_mb
from src.core.auth import get_current_user
from src.core.config import settings
from src.core.integrations import resolve_integrations
from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameLink, GameStatus
from src.database.models.game_checklist_item import GameChecklistItem
from src.database.models.game_field_change import GameFieldChange
from src.database.models.game_file_item import GameFileItem
from src.database.models.media_item import MediaItem
from src.database.models.user import User
from src.database.models.user_scan_settings import UserScanSettings
from src.database.session import get_db
from src.features.metadata.games.search import search_game_metadata
from src.features.trash.game_trash import move_game_to_trash, restore_game_from_trash
from src.features.trash.media_trash import move_media_file_to_trash, restore_media_file_from_trash
from src.features.trash.sweep import RETENTION_SECONDS
from src.helpers.media import MediaKind, classify_media, list_media, media_subdir, save_media_bytes
from src.helpers.save_game_asset import (
    ASSET_FILENAMES,
    AssetKind,
    create_game_folder,
    save_game_asset,
)
from src.api.routes.game_notes import router as game_notes_router
from src.api.routes.game_profiles import router as game_profiles_router
from src.api.routes.game_helpers import _validate_asset_kind

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
    dependencies=[Depends(get_current_user)],
)
router.include_router(game_notes_router)
router.include_router(game_profiles_router)

_DATA_ROOT = Path("/data/users")
_NOTE_NAME_PATTERN = re.compile(r"^[^\x00-\x1f\x7f/\\]+$")
_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)

_DB_DEPENDENCY = Depends(get_db)
_CURRENT_USER_DEPENDENCY = Depends(get_current_user)
_FILE_UPLOAD = File(...)
_BODY_DOTDOTDOT = Body(...)
_NONE_FORM = Form(None)
_NONE_QUERY_STATUS = Query(default=None, alias="status")


class NoteWrite(BaseModel):
    """Request body used to create or update a game note."""

    content: str


class NoteRename(BaseModel):
    """Request body used to rename a game note."""

    new_name: str


class MetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    steamgriddb_configured: bool = False
    provider_errors: list[str] = []
    results: list[dict]


class AssetUrlRequest(BaseModel):
    url: str



def _scan_settings_to_preferences(scan_settings: UserScanSettings) -> dict:
    return {
        "provider_order": scan_settings.provider_order,
        "image_provider_order": scan_settings.image_provider_order,
        "save_developer": scan_settings.save_developer,
        "save_publisher": scan_settings.save_publisher,
        "save_series": scan_settings.save_series,
        "save_tags": scan_settings.save_tags,
        "save_features": scan_settings.save_features,
        "save_description": scan_settings.save_description,
        "save_age_rating": scan_settings.save_age_rating,
        "save_release_date": scan_settings.save_release_date,
        "save_time_to_beat": scan_settings.save_time_to_beat,
        "save_key_art": scan_settings.save_key_art,
        "save_banner": scan_settings.save_banner,
        "save_logo": scan_settings.save_logo,
        "save_icon": scan_settings.save_icon,
    }


@router.get("/metadata/search", response_model=MetadataSearchResponse)
async def search_metadata(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
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
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    try:
        result = await asyncio.to_thread(
            search_game_metadata,
            query.strip(),
            limit,
            current_user.steamgriddb_api_key,
            preferences,
            current_user,
            app_integrations.igdb_client_id,
            app_integrations.igdb_client_secret,
        )
    except Exception as exc:
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


@router.get("/{game_id}/assets/{asset_kind}", response_class=FileResponse)
async def get_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    """Return a stored PNG asset for a game."""
    _validate_asset_kind(asset_kind)

    game = await _get_game_or_404(game_id, db, current_user.id)
    asset_path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / game.folder_location
        / ASSET_FILENAMES[asset_kind]
    )
    if not asset_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Asset '{asset_kind}' has not been uploaded for game {game_id}.",
        )

    return FileResponse(
        asset_path,
        media_type="image/png",
        # was "no-store, max-age=0" — meant the browser re-downloaded every
        # cover/banner on every scroll, reload, and revisit, even when
        # nothing changed. Starlette's FileResponse already sets
        # Last-Modified/ETag from the file's own stat, so a "revalidate"
        # cache still gets a cheap 304 instead of a full re-fetch the
        # instant an asset actually changes (a refresh/re-sync overwrites
        # the file in place, changing its mtime).
        headers={"Cache-Control": "private, max-age=3600, must-revalidate"},
    )


def _derive_sort_title(title: str) -> str:
    """'The Witcher 3' -> 'witcher 3' so articles don't affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


# the same set a metadata search/refresh is allowed to overwrite (see the
# scan-settings save_* toggles in ScanSettingsSection.vue). A field outside
# this set (folder_location, favorite, playtime, ...) isn't "metadata" in
# that sense, so history only tracks what a provider could plausibly have
# changed underneath the user
FIELD_CHANGE_TRACKED_FIELDS = {
    "developer",
    "publisher",
    "series",
    "tags",
    "features",
    "description",
    "age_rating",
    "release_date",
    "time_to_beat_hours",
}


def _field_change_value_to_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join(str(v) for v in value) if value else None
    return str(value)


def _record_field_changes(game: Game, updates: dict, db: AsyncSession) -> None:
    now = int(time.time())
    for field in FIELD_CHANGE_TRACKED_FIELDS & updates.keys():
        old_text = _field_change_value_to_text(getattr(game, field))
        new_text = _field_change_value_to_text(updates[field])
        if old_text == new_text:
            continue
        db.add(
            GameFieldChange(
                game_id=game.id,
                field_name=field,
                old_value=old_text,
                new_value=new_text,
                changed_at=now,
            )
        )


# columns a PATCH can't blank: an explicit null for one of these means "no
# change", not "clear it" (the database would reject the NULL anyway, which
# used to surface as a misleading duplicate-folder error)
_NON_NULLABLE_UPDATE_FIELDS = frozenset(
    {
        "title",
        "sort_title",
        "created_at",
        "folder_location",
        "status",
        "favorite",
        "profiles_enabled",
        "osrs_stats_enabled",
        "playtime_seconds",
        "tags",
        "features",
        "collections",
    }
)


def _drop_nulls_for_required_fields(updates: dict) -> dict:
    cleaned = {
        field: value
        for field, value in updates.items()
        if value is not None or field not in _NON_NULLABLE_UPDATE_FIELDS
    }
    # a cleared sorting name is still a request: re-derive it from the title
    if "sort_title" in updates and updates["sort_title"] is None:
        cleaned["sort_title"] = ""
    return cleaned


def _duplicate_folder_error(folder_name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "duplicate_folder_location",
            "field": "folder_location",
            "value": folder_name,
            "message": f"A game with folder_location '{folder_name}' already exists.",
        },
    )


async def _ensure_folder_location_available(
    folder_name: str,
    user_id: UUID,
    db: AsyncSession,
    exclude_game_id: UUID | None = None,
) -> None:
    stmt = select(Game.id).where(
        Game.user_id == user_id,
        Game.folder_location == folder_name,
        Game.deleted_at.is_(None),
    )
    if exclude_game_id is not None:
        stmt = stmt.where(Game.id != exclude_game_id)

    existing = await db.scalar(stmt)
    if existing is not None:
        raise _duplicate_folder_error(folder_name)




async def _get_game_or_404(
    game_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Game:
    stmt = select(Game).where(Game.id == game_id, Game.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Game.deleted_at.is_(None))
    game = await db.scalar(stmt)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game


@router.get("/achievements-summary")
async def get_achievements_summary(
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, dict[str, int]]:
    """Per-game {total, unlocked} counts for every one of the caller's games
    that has any achievements at all, in one grouped query — powers the
    completion badge on library/card views without an N+1 request per game."""
    rows = await db.execute(
        select(
            Achievement.game_id,
            func.count(Achievement.id),
            func.sum(func.cast(Achievement.unlocked, Integer)),
        )
        .join(Game, Game.id == Achievement.game_id)
        .where(Game.user_id == current_user.id, Game.deleted_at.is_(None))
        .group_by(Achievement.game_id)
    )
    return {
        str(game_id): {"total": total, "unlocked": unlocked or 0}
        for game_id, total, unlocked in rows
    }


@router.get("/{game_id}/achievements")
async def list_game_achievements(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> list[dict]:
    """Achievements/trophies pulled in by a library sync (Settings ->
    Metadata/API -> Steam/PlayStation/RetroAchievements). Empty until that
    game has been synced at least once — this never calls out to a
    provider itself, it only reads what's already stored."""
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(Achievement)
        .where(Achievement.game_id == game_id)
        .order_by(Achievement.unlocked.desc(), Achievement.name)
    )
    return [
        {
            "id": str(a.id),
            "provider": a.provider,
            "name": a.name,
            "description": a.description,
            "icon_url": a.icon_url,
            "unlocked": a.unlocked,
            "unlocked_at": a.unlocked_at,
        }
        for a in result.scalars().all()
    ]


@router.post(
    "/{game_id}/assets/{asset_kind}",
    responses={
        status.HTTP_200_OK: {"description": "Image uploaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid asset kind or upload"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def upload_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    file: UploadFile = _FILE_UPLOAD,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Upload and persist artwork for a game."""
    if asset_kind not in ALLOWED_ASSET_KINDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported asset kind '{asset_kind}'. Supported values: {sorted(ALLOWED_ASSET_KINDS)}",
        )

    await _get_game_or_404(game_id, db, current_user.id)

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is required.",
        )

    # Do not trust the browser-supplied MIME type here. Some valid image
    # files are reported as application/octet-stream (or with no type at all).
    # save_game_asset decodes the actual image bytes with Pillow, which gives
    # us the real validation without rejecting otherwise valid manual uploads.
    image_bytes = await file.read()
    max_upload_mb = await get_max_upload_size_mb(db)
    max_bytes = max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is larger than the {max_upload_mb} MB limit.",
        )

    try:
        target_path = await save_game_asset(image_bytes, game_id, asset_kind)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not process image: {exc}",
        ) from exc

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(target_path),
        "status": "saved",
    }


@router.post(
    "/{game_id}/assets/{asset_kind}/from-url",
    responses={
        status.HTTP_200_OK: {"description": "Image downloaded and resized"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid URL or image"},
        status.HTTP_404_NOT_FOUND: {"description": "Game not found"},
    },
)
async def download_game_asset(
    game_id: UUID,
    asset_kind: AssetKind,
    payload: AssetUrlRequest,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Download an image URL and persist it as a normalized game asset."""
    _validate_asset_kind(asset_kind)

    await _get_game_or_404(game_id, db, current_user.id)
    parsed_url = urlparse(payload.url)
    if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Image URL must use http or https."
        )

    try:
        response = await asyncio.to_thread(requests.get, payload.url, timeout=20)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not download image: {exc}"
        ) from exc

    content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
    if not content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="URL did not return an image."
        )
    image_bytes = response.content
    max_upload_mb = await get_max_upload_size_mb(db)
    max_bytes = max_upload_mb * 1024 * 1024
    if len(image_bytes) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image is larger than the {max_upload_mb} MB limit.",
        )

    try:
        output_path = await save_game_asset(image_bytes, game_id, asset_kind)
    except (OSError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not save image: {exc}"
        ) from exc

    return {
        "game_id": str(game_id),
        "asset_kind": asset_kind,
        "path": str(output_path),
        "status": "saved",
    }


def _media_item_to_dict(item: MediaItem, game_id: UUID) -> dict:
    return {
        "id": str(item.id),
        "filename": item.filename,
        "kind": item.kind,
        "url": f"/api/game/{game_id}/screenshots/{item.kind}/{item.filename}",
        "tags": item.tags,
        "note": item.note,
        "linked_achievement_id": str(item.linked_achievement_id)
        if item.linked_achievement_id
        else None,
        "profile_id": str(item.profile_id) if item.profile_id else None,
        "created_at": item.created_at,
    }


@router.post("/{game_id}/screenshots")
async def upload_game_screenshots(
    game_id: UUID,
    files: list[UploadFile] = _FILE_UPLOAD,
    profile_id: UUID | None = _NONE_FORM,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Bulk upload — accepts any mix of images, videos, and audio in one
    request. Images become screenshots, videos become clips, audio becomes
    soundtrack; anything else is rejected per-file (the rest still save).
    Each saved file gets a MediaItem row (not just a file on disk) so it can
    be tagged, noted, and linked to an achievement afterward. An optional
    profile_id tags the whole batch to one account (e.g. an OSRS ironman) —
    useful for a "levelup dump from this account" upload in one go."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing."
        )
    if profile_id is not None:
        await _get_profile_or_404(profile_id, game_id, db)

    results: list[dict] = []
    for file in files:
        kind = classify_media(file.content_type, file.filename or "")
        if kind is None:
            results.append(
                {
                    "filename": file.filename,
                    "status": "rejected",
                    "reason": "Unsupported file type.",
                }
            )
            continue

        # clips/soundtrack get a much larger cap than images — a real video
        # clip routinely exceeds a cover-art-sized limit
        limit_mb = (
            settings.MAX_CLIP_SIZE_MB
            if kind in ("clip", "soundtrack")
            else await get_max_upload_size_mb(db)
        )
        max_bytes = limit_mb * 1024 * 1024

        data = await file.read()
        if len(data) > max_bytes:
            results.append(
                {
                    "filename": file.filename,
                    "status": "rejected",
                    "reason": f"Larger than {limit_mb} MB.",
                }
            )
            continue

        dest_dir = (
            _DATA_ROOT / str(game.user_id) / "games" / game.folder_location / media_subdir(kind)
        )
        saved_path = save_media_bytes(data, dest_dir, file.filename or "file")
        db.add(
            MediaItem(game_id=game_id, kind=kind, filename=saved_path.name, profile_id=profile_id)
        )
        results.append({"filename": saved_path.name, "status": "saved", "kind": kind})

    await db.commit()
    return {"results": results}


@router.get("/{game_id}/screenshots")
async def list_game_screenshots(
    game_id: UUID,
    profile_id: UUID | None = _NONE_FORM,
    unscoped_only: bool = Query(False, description="Only items with no profile_id set."),
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    stmt = select(MediaItem).where(MediaItem.game_id == game_id, MediaItem.deleted_at.is_(None))
    if profile_id is not None:
        stmt = stmt.where(MediaItem.profile_id == profile_id)
    elif unscoped_only:
        stmt = stmt.where(MediaItem.profile_id.is_(None))
    result = await db.execute(stmt.order_by(MediaItem.created_at.desc()))
    return {"media": [_media_item_to_dict(item, game_id) for item in result.scalars().all()]}


@router.get("/{game_id}/screenshots/{kind}/{filename}", response_class=FileResponse)
async def get_game_screenshot(
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    game = await _get_game_or_404(game_id, db, current_user.id)
    path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / (game.folder_location or "")
        / media_subdir(kind)
        / Path(filename).name
    )
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media file not found.")
    return FileResponse(path)


class MediaItemUpdate(BaseModel):
    tags: list[str] | None = None
    note: str | None = None
    linked_achievement_id: UUID | None = None
    profile_id: UUID | None = None


@router.patch("/{game_id}/screenshots/{media_id}")
async def update_media_item(
    game_id: UUID,
    media_id: UUID,
    payload: MediaItemUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(MediaItem.id == media_id, MediaItem.game_id == game_id)
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return _media_item_to_dict(item, game_id)


@router.delete("/{game_id}/screenshots/{kind}/{filename}")
async def delete_game_screenshot(
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Soft-delete: moves the file to trash and marks its row deleted
    rather than removing it — restorable for 7 days, same as game
    archives (features/trash/sweep.py does the eventual real deletion)."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.game_id == game_id,
            MediaItem.kind == kind,
            MediaItem.filename == filename,
            MediaItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media item not found.")
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    path = game_dir / media_subdir(kind) / Path(filename).name
    move_media_file_to_trash(path, game_dir, kind)
    item.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "filename": filename}


@router.get("/{game_id}/screenshots/trash")
async def list_game_screenshot_trash(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(MediaItem)
        .where(MediaItem.game_id == game_id, MediaItem.deleted_at.is_not(None))
        .order_by(MediaItem.deleted_at.desc())
    )
    media = []
    for item in result.scalars().all():
        assert item.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        media.append(
            {
                **_media_item_to_dict(item, game_id),
                "deleted_at": item.deleted_at,
                "purge_at": item.deleted_at + RETENTION_SECONDS,
            }
        )
    return {"media": media}


@router.post("/{game_id}/screenshots/{kind}/{filename}/restore")
async def restore_game_screenshot(
    game_id: UUID,
    kind: MediaKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    game = await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(MediaItem).where(
            MediaItem.game_id == game_id,
            MediaItem.kind == kind,
            MediaItem.filename == filename,
            MediaItem.deleted_at.is_not(None),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Deleted media item not found."
        )
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    restore_media_file_from_trash(filename, game_dir / media_subdir(kind), game_dir, kind)
    item.deleted_at = None
    await db.commit()
    return _media_item_to_dict(item, game_id)


GameFileKind = Literal["doc", "modpack"]
# "save" and "world_save" moved to game_archives.py — named, versioned
# archives instead of an anonymous single flat file each

_GAME_FILE_SUBDIRS: dict[GameFileKind, str] = {
    "doc": "docs",
    "modpack": "modpacks",
}


def _game_file_subdir(kind: GameFileKind) -> str:
    return _GAME_FILE_SUBDIRS[kind]


async def _sync_game_file_items(game_id: UUID, game_dir: Path, db: AsyncSession) -> None:
    """Docs/modpacks used to be tracked only on disk, with no DB row at
    all — this backfills a row (created_at from the file's mtime) for
    anything already sitting in the active folder that doesn't have one
    yet, so existing files from before this migration still show up
    without a one-time manual migration script (same approach as
    media.py's _sync_inbox_items)."""
    existing = await db.execute(
        select(GameFileItem.kind, GameFileItem.filename).where(
            GameFileItem.game_id == game_id, GameFileItem.deleted_at.is_(None)
        )
    )
    known = {(kind, filename) for kind, filename in existing.all()}
    added = False
    for kind in ("doc", "modpack"):
        for filename in list_media(game_dir / _game_file_subdir(kind)):  # type: ignore[arg-type]
            if (kind, filename) in known:
                continue
            path = game_dir / _game_file_subdir(kind) / filename  # type: ignore[arg-type]
            try:
                mtime = int(path.stat().st_mtime)
            except OSError:
                mtime = int(time.time())
            db.add(GameFileItem(game_id=game_id, kind=kind, filename=filename, created_at=mtime))
            added = True
    if added:
        await db.commit()


@router.post("/{game_id}/files/{kind}")
async def upload_game_files(
    game_id: UUID,
    kind: GameFileKind,
    files: list[UploadFile] = _FILE_UPLOAD,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Generic file attachments for a game — docs/manuals and modpacks can
    be almost any format, so unlike screenshots/clips there's no
    content-type validation, just a size cap."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Game folder_location is missing."
        )

    # a modpack zip is routinely hundreds of MB to a few GB — far past a
    # doc-sized limit
    limit_mb = (
        settings.MAX_WORLD_SAVE_SIZE_MB if kind == "modpack" else await get_max_upload_size_mb(db)
    )
    max_bytes = limit_mb * 1024 * 1024
    results: list[dict] = []
    for file in files:
        data = await file.read()
        if len(data) > max_bytes:
            results.append(
                {
                    "filename": file.filename,
                    "status": "rejected",
                    "reason": f"Larger than {limit_mb} MB.",
                }
            )
            continue
        dest_dir = (
            _DATA_ROOT
            / str(game.user_id)
            / "games"
            / game.folder_location
            / _game_file_subdir(kind)
        )
        saved_path = save_media_bytes(data, dest_dir, file.filename or "file")
        db.add(GameFileItem(game_id=game_id, kind=kind, filename=saved_path.name))
        results.append({"filename": saved_path.name, "status": "saved", "size": len(data)})

    await db.commit()
    return {"results": results}


@router.get("/{game_id}/files/{kind}")
async def list_game_files(
    game_id: UUID,
    kind: GameFileKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    game = await _get_game_or_404(game_id, db, current_user.id)
    if not game.folder_location:
        return {"files": []}
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / game.folder_location
    await _sync_game_file_items(game_id, game_dir, db)
    result = await db.execute(
        select(GameFileItem)
        .where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.deleted_at.is_(None),
        )
        .order_by(GameFileItem.filename)
    )
    return {
        "files": [
            {
                "filename": item.filename,
                "size": (game_dir / _game_file_subdir(kind) / item.filename).stat().st_size
                if (game_dir / _game_file_subdir(kind) / item.filename).is_file()
                else 0,
                "url": f"/api/game/{game_id}/files/{kind}/{item.filename}",
            }
            for item in result.scalars().all()
        ]
    }


@router.get("/{game_id}/files/{kind}/trash")
async def list_game_file_trash(
    game_id: UUID,
    kind: GameFileKind,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(GameFileItem)
        .where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.deleted_at.is_not(None),
        )
        .order_by(GameFileItem.deleted_at.desc())
    )
    files = []
    for item in result.scalars().all():
        assert item.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        files.append(
            {
                "filename": item.filename,
                "deleted_at": item.deleted_at,
                "purge_at": item.deleted_at + RETENTION_SECONDS,
            }
        )
    return {"files": files}


@router.get("/{game_id}/files/{kind}/{filename}", response_class=FileResponse)
async def get_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> FileResponse:
    game = await _get_game_or_404(game_id, db, current_user.id)
    path = (
        _DATA_ROOT
        / str(game.user_id)
        / "games"
        / (game.folder_location or "")
        / _game_file_subdir(kind)
        / Path(filename).name
    )
    if not path.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    # arbitrary user files (saves/docs) should download, not attempt to
    # render inline the way an image/video screenshot asset does — the
    # random 8-char prefix save_media_bytes adds to dedupe filenames is
    # stripped back off for the name the browser actually saves it as
    original_name = Path(filename).name.split("_", 1)[-1]
    return FileResponse(path, filename=original_name, media_type="application/octet-stream")


@router.delete("/{game_id}/files/{kind}/{filename}")
async def delete_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Soft-delete: moves the file to trash and marks its row deleted
    rather than removing it — restorable for 7 days, same as every other
    delete path in the app (features/trash/sweep.py does the eventual
    real deletion)."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    await _sync_game_file_items(game_id, game_dir, db)
    name = Path(filename).name
    item = await db.scalar(
        select(GameFileItem).where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.filename == name,
            GameFileItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found.")
    path = game_dir / _game_file_subdir(kind) / name
    move_media_file_to_trash(path, game_dir, kind)
    item.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "filename": name}


@router.post("/{game_id}/files/{kind}/{filename}/restore")
async def restore_game_file(
    game_id: UUID,
    kind: GameFileKind,
    filename: str,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    game = await _get_game_or_404(game_id, db, current_user.id)
    name = Path(filename).name
    item = await db.scalar(
        select(GameFileItem).where(
            GameFileItem.game_id == game_id,
            GameFileItem.kind == kind,
            GameFileItem.filename == name,
            GameFileItem.deleted_at.is_not(None),
        )
    )
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Deleted file not found.")
    game_dir = _DATA_ROOT / str(game.user_id) / "games" / (game.folder_location or "")
    restore_media_file_from_trash(name, game_dir / _game_file_subdir(kind), game_dir, kind)
    item.deleted_at = None
    await db.commit()
    return {"status": "restored", "filename": name}


