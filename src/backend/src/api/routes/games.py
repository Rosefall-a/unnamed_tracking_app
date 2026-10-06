"""API routes for managing games, notes, and game artwork."""

import time
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy import Integer, func, select
from sqlalchemy import cast as sql_cast
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from src.api.routes import (
    game_assets,
    game_checklists,
    game_files,
    game_metadata,
    game_notes,
    game_profiles,
)
from src.api.routes.game_assets import (
    AssetUrlRequest,
    DetectDatesRequest,
    MediaItemUpdate,
    _media_item_to_dict,
    _thumb_dir,
    delete_game_screenshot,
    detect_media_dates,
    download_game_asset,
    get_clip_thumbnail,
    get_game_asset,
    get_game_screenshot,
    list_game_screenshot_trash,
    list_game_screenshots,
    restore_game_screenshot,
    save_clip_thumbnail,
    update_media_item,
    upload_game_asset,
    upload_game_screenshots,
)
from src.api.routes.game_checklists import (
    ChecklistItemUpdate,
    ChecklistItemWrite,
    ChecklistReorder,
    _checklist_item_to_dict,
    create_checklist_item,
    delete_checklist_item,
    list_game_checklist,
    reorder_checklist,
    update_checklist_item,
)
from src.api.routes.game_files import (
    GameFileUpdate,
    _game_file_subdir,
    _game_file_to_dict,
    _sync_game_file_items,
    delete_game_file,
    get_game_file,
    list_game_file_trash,
    list_game_files,
    restore_game_file,
    update_game_file,
    upload_game_files,
)
from src.api.routes.game_metadata import (
    _GAME_METADATA_FIELDS,
    MetadataRefreshRequest,
    MetadataSearchResponse,
    _metadata_value_is_present,
    _normalize_metadata_title,
    refresh_game_metadata,
    search_metadata,
)
from src.api.routes.game_notes import (
    NoteRename,
    NoteWrite,
    create_game_note,
    delete_game_note,
    get_game_note,
    list_game_note_summaries,
    list_game_notes,
    rename_game_note,
    update_game_note,
)
from src.api.routes.game_profiles import (
    ProfileUpdate,
    ProfileWrite,
    WiseOldManSyncRequest,
    _get_profile_or_404,
    _profile_to_dict,
    _record_stat_snapshot,
    create_game_profile,
    delete_game_profile,
    get_profile_stat_history,
    list_game_profile_trash,
    list_game_profiles,
    restore_game_profile,
    sync_profile_wiseoldman,
    update_game_profile,
)
from src.api.routes.utils.games import (
    _DATA_ROOT,
    _NON_NULLABLE_UPDATE_FIELDS,
    _NOTE_NAME_PATTERN,
    ALLOWED_ASSET_KINDS,
    FIELD_CHANGE_TRACKED_FIELDS,
    _derive_sort_title,
    _drop_nulls_for_required_fields,
    _duplicate_folder_error,
    _ensure_folder_location_available,
    _field_change_value_to_text,
    _game_note_path,
    _get_game_or_404,
    _normalize_note_name,
    _note_summary,
    _record_field_changes,
    _scan_settings_to_preferences,
)
from src.api.schemas.game import (
    GameBulkUpdate,
    GameCreate,
    GameFieldChangeRead,
    GameRead,
    GameUpdate,
)
from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameLink, GameStatus
from src.database.models.game_field_change import GameFieldChange
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.locked_fields import apply_updates_with_locking
from src.features.trash.game_trash import move_game_to_trash, restore_game_from_trash
from src.features.trash.sweep import RETENTION_SECONDS
from src.helpers.save_game_asset import (
    create_game_folder,
)

_QUERY_DEFAULT = Query(..., min_length=2, max_length=100)
_LIMIT_DEFAULT = Query(default=8, ge=1, le=20)
_INCLUDE_IMAGES_DEFAULT = Query(default=True)
_FILES_DEFAULT = File(None, alias="files")
_FILE_DEFAULT = File(None, alias="file")
_UNSCOPED_ONLY_DEFAULT = Query(False, description="Only items with no profile_id set.")
_FAVORITE_DEFAULT = Query(default=None)
_SEARCH_DEFAULT = Query(default=None, description="Case-insensitive title search")
_SKIP_DEFAULT = Query(default=0, ge=0)
_LIMIT_DEFAULT_2 = Query(default=50, ge=1, le=200)

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
    dependencies=[Depends(get_current_user)],
)


_DB_DEPENDENCY = Depends(get_db)
_CURRENT_USER_DEPENDENCY = Depends(get_current_user)
# one instance per field name: FastAPI names a File() after the first
# parameter it is used on, so sharing one made `files` demand a field "file"
_FILE_UPLOAD = File(...)
_FILES_UPLOAD = File(...)
_BODY_DOTDOTDOT = Body(...)
_NONE_FORM = Form(None)
_MODIFIED_FORM = Form(None)
_FILE_MODIFIED_FORM = Form(None)
_NONE_QUERY_STATUS = Query(default=None, alias="status")


router.include_router(game_metadata.search_router)


router.include_router(game_assets.asset_read_router)


# the same set a metadata search/refresh is allowed to overwrite (see the
# scan-settings save_* toggles in ScanSettingsSection.vue). A field outside
# this set (folder_location, favorite, playtime, ...) isn't "metadata" in
# that sense, so history only tracks what a provider could plausibly have
# changed underneath the user


# columns a PATCH can't blank: an explicit null for one of these means "no
# change", not "clear it" (the database would reject the NULL anyway, which
# used to surface as a misleading duplicate-folder error)


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
            sql_count(Achievement.id),
            func.sum(sql_cast(Achievement.unlocked, Integer)),
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
            "hidden": a.hidden,
            "global_percent": a.global_percent,
            # how the provider classifies it (RetroAchievements only): one of
            # progression, missable or win_condition
            "tier": a.tier,
        }
        for a in result.scalars().all()
    ]


router.include_router(game_assets.router)


router.include_router(game_files.router)


router.include_router(game_notes.crud_router)


router.include_router(game_profiles.router)


router.include_router(game_checklists.router)


async def _find_playnite_game(payload: GameCreate, user_id: UUID, db: AsyncSession) -> Game | None:
    """The active game a Playnite create should reconcile onto, if any: the
    one already carrying this GUID, else the one in the requested folder when
    it isn't claimed by a different Playnite entry (then it's a genuine
    folder conflict and the caller reports it). A folder match without a
    GUID is adopted by recording the GUID on it."""
    active = (Game.user_id == user_id, Game.deleted_at.is_(None))
    by_guid = await db.scalar(
        select(Game).where(*active, Game.playnite_guid == payload.playnite_guid).limit(1)
    )
    if by_guid is not None:
        return by_guid
    by_folder = await db.scalar(
        select(Game).where(*active, Game.folder_location == payload.folder_location)
    )
    if by_folder is None or by_folder.playnite_guid not in (None, payload.playnite_guid):
        return None
    if by_folder.playnite_guid is None:
        by_folder.playnite_guid = payload.playnite_guid
        await db.commit()
        await db.refresh(by_folder)
    return by_folder


async def _validate_game_relationship(
    parent_game_id: UUID | None,
    relationship_type: str | None,
    db: AsyncSession,
    user_id: UUID,
    game_id: UUID | None = None,
) -> None:
    """A relationship_type only makes sense alongside a parent_game_id
    (GameUpdate can't enforce this itself — a partial update might set only
    one of the two fields in a given request, with the other already
    correct from an earlier one). Also blocks a game being its own parent
    and pointing at a parent that isn't actually this user's."""
    if relationship_type is not None and parent_game_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="relationship_type requires parent_game_id to be set.",
        )
    if parent_game_id is None:
        return
    if game_id is not None and parent_game_id == game_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A game cannot be its own parent."
        )
    parent = await db.scalar(
        select(Game).where(
            Game.id == parent_game_id, Game.user_id == user_id, Game.deleted_at.is_(None)
        )
    )
    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="parent_game_id does not exist."
        )


@router.post(
    "/create",
    response_model=GameRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Duplicate folder_location",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "duplicate_folder_location",
                            "field": "folder_location",
                            "value": "ExistingFolder",
                            "message": "A game with folder_location 'ExistingFolder' already exists.",
                        }
                    }
                }
            },
        }
    },
)
async def create_game(
    payload: GameCreate,
    response: Response,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Game:
    """Create a game after validating its folder location.

    A create that carries a `playnite_guid` is idempotent: if this user
    already has that Playnite game (by GUID, or by folder name with no other
    GUID claiming it) the existing game is returned with 200 instead of a
    duplicate-folder failure, so a repeated or concurrent Playnite sync
    reconciles rather than erroring (#184). A manual create (no GUID) still
    gets 409 for a folder name that's taken."""
    if payload.playnite_guid is not None:
        existing = await _find_playnite_game(payload, current_user.id, db)
        if existing is not None:
            response.status_code = status.HTTP_200_OK
            return existing

    await _ensure_folder_location_available(payload.folder_location, current_user.id, db)
    await _validate_game_relationship(
        payload.parent_game_id, payload.relationship_type, db, current_user.id
    )

    data = payload.model_dump()
    data["user_id"] = current_user.id
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])
    # an explicit None would bypass the column default and violate NOT NULL
    if data.get("created_at") is None:
        data.pop("created_at", None)

    # `links` is a relationship, not a plain column — the constructor needs
    # actual GameLink instances, not the raw {label, url} dicts model_dump
    # produces
    link_rows = [GameLink(label=link["label"], url=link["url"]) for link in data.pop("links", [])]

    game = Game(**data)
    game.links = link_rows
    db.add(game)

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        # another sync created the same Playnite game between the check
        # above and this insert: hand back the row that won the race
        if payload.playnite_guid is not None:
            existing = await _find_playnite_game(payload, current_user.id, db)
            if existing is not None:
                response.status_code = status.HTTP_200_OK
                return existing
        raise _duplicate_folder_error(payload.folder_location) from exc

    create_game_folder(game.user_id, game.folder_location)
    return game


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-positional-arguments
@router.get("/list", response_model=list[GameRead])
async def list_games(
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
    status_filter: GameStatus | None = _NONE_QUERY_STATUS,
    favorite: bool | None = _FAVORITE_DEFAULT,
    search: str | None = _SEARCH_DEFAULT,
    skip: int = _SKIP_DEFAULT,
    limit: int = _LIMIT_DEFAULT_2,
) -> list[Game]:
    """Return games filtered by status, favorite flag, or title search."""
    stmt = select(Game).where(Game.user_id == current_user.id, Game.deleted_at.is_(None))

    if status_filter is not None:
        stmt = stmt.where(Game.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(Game.favorite == favorite)
    if search:
        stmt = stmt.where(Game.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(Game.sort_title).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


# pylint: enable=too-many-positional-arguments


@router.get("/get/{game_id}", response_model=GameRead)
async def get_game(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Game:
    """Return one game by ID."""
    return await _get_game_or_404(game_id, db, current_user.id)


@router.get("/{game_id}/variants", response_model=list[GameRead])
async def get_game_variants(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> list[Game]:
    """Every game whose parent_game_id points at this one — the reverse of
    the parent breadcrumb (GameDetail.vue's `parentGameTitle`). A base game
    like Minecraft has no idea its modpacks exist otherwise, since the FK
    only points child -> parent."""
    await _get_game_or_404(game_id, db, current_user.id)
    stmt = (
        select(Game)
        .where(
            Game.user_id == current_user.id,
            Game.parent_game_id == game_id,
            Game.deleted_at.is_(None),
        )
        .order_by(Game.sort_title)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch(
    "/update/{game_id}",
    response_model=GameRead,
    responses={
        status.HTTP_409_CONFLICT: {
            "description": "Duplicate folder_location",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "duplicate_folder_location",
                            "field": "folder_location",
                            "value": "ExistingFolder",
                            "message": "A game with folder_location 'ExistingFolder' already exists.",
                        }
                    }
                }
            },
        }
    },
)
async def update_game(
    game_id: UUID,
    payload: GameUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Game:
    """Update a game and keep its derived sort title synchronized."""
    game = await _get_game_or_404(game_id, db, current_user.id)

    updates = _drop_nulls_for_required_fields(payload.model_dump(exclude_unset=True))

    if "folder_location" in updates and updates["folder_location"] is not None:
        await _ensure_folder_location_available(
            updates["folder_location"], current_user.id, db, exclude_game_id=game_id
        )

    if "parent_game_id" in updates or "relationship_type" in updates:
        effective_parent = updates.get("parent_game_id", game.parent_game_id)
        effective_relationship = updates.get("relationship_type", game.relationship_type)
        await _validate_game_relationship(
            effective_parent, effective_relationship, db, current_user.id, game_id
        )

    # `links` is a relationship, not a plain column — setattr needs actual
    # GameLink instances, not the raw {label, url} dicts model_dump
    # produces. Reassigning the whole list lets cascade="all, delete-orphan"
    # (see Game.links) drop whichever rows aren't in the new list.
    if "links" in updates:
        new_links = updates.pop("links") or []
        game.links = [GameLink(label=link["label"], url=link["url"]) for link in new_links]

    _record_field_changes(game, updates, db)
    apply_updates_with_locking(game, updates, frozenset(_GAME_METADATA_FIELDS))

    for field, value in updates.items():
        setattr(game, field, value)

    # Keep sort_title in sync if title changed but sort_title wasn't explicitly
    # set, or was cleared (a blank sorting name means "sort by the title")
    if ("title" in updates and "sort_title" not in updates) or (
        "sort_title" in updates and not updates["sort_title"]
    ):
        game.sort_title = _derive_sort_title(game.title)

    # first time this game reaches Mastered, record when — a later status
    # change away from and back to Mastered doesn't overwrite it, so it
    # stays "when I first 100%'d this" rather than "when I last did"
    if updates.get("status") == GameStatus.MASTERED and game.completion_date is None:
        game.completion_date = int(time.time())

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _duplicate_folder_error(game.folder_location) from exc

    return game


router.include_router(game_metadata.router)


@router.get("/{game_id}/field-changes", response_model=list[GameFieldChangeRead])
async def list_field_changes(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> list[GameFieldChange]:
    """Most-recent-first metadata history for one game."""
    await _get_game_or_404(game_id, db, current_user.id)
    stmt = (
        select(GameFieldChange)
        .where(GameFieldChange.game_id == game_id)
        .order_by(GameFieldChange.changed_at.desc())
        .limit(100)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.patch("/bulk-update")
async def bulk_update_games(
    payload: GameBulkUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, int]:
    """Apply the same field values to many of the caller's games at once —
    e.g. fixing status across a batch, or filling in developer/publisher
    for titles a metadata search couldn't confidently match on its own."""
    updates = _drop_nulls_for_required_fields(
        payload.model_dump(exclude_unset=True, exclude={"game_ids"})
    )
    if not updates:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update.")

    result = await db.execute(
        select(Game).where(
            Game.user_id == current_user.id,
            Game.id.in_(payload.game_ids),
            Game.deleted_at.is_(None),
        )
    )
    games = result.scalars().all()
    for game in games:
        for field, value in updates.items():
            setattr(game, field, value)
        if updates.get("status") == GameStatus.MASTERED and game.completion_date is None:
            game.completion_date = int(time.time())
    await db.commit()
    return {"updated": len(games)}


@router.delete("/delete/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> None:
    """Soft-delete: moves the game's entire folder to trash and marks the
    row deleted rather than removing anything — restorable for 7 days.
    This is the highest-blast-radius delete in the app (screenshots,
    clips, notes, achievements, saves, everything lives under this one
    folder), so it gets the same protection as game archives instead of
    the instant, permanent delete it had before."""
    game = await _get_game_or_404(game_id, db, current_user.id)
    if game.folder_location:
        move_game_to_trash(
            _DATA_ROOT / str(game.user_id) / "games" / game.folder_location, _DATA_ROOT, game_id
        )
    game.deleted_at = int(time.time())
    await db.commit()


@router.get("/trash")
async def list_game_trash(
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> list[dict]:
    result = await db.execute(
        select(Game)
        .where(Game.user_id == current_user.id, Game.deleted_at.is_not(None))
        .order_by(Game.deleted_at.desc())
    )
    trashed = []
    for game in result.scalars().all():
        assert game.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        trashed.append(
            {
                "id": str(game.id),
                "title": game.title,
                "deleted_at": game.deleted_at,
                "purge_at": game.deleted_at + RETENTION_SECONDS,
            }
        )
    return trashed


@router.post("/{game_id}/restore", response_model=GameRead)
async def restore_game(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> Game:
    game = await _get_game_or_404(game_id, db, current_user.id, include_deleted=True)
    if game.deleted_at is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Game isn't deleted.")
    if game.folder_location:
        # a new active game may have claimed this folder name while this one
        # sat in trash (the partial unique index only protects active rows) —
        # check before touching any files, not after, so a rejected restore
        # never leaves the folder half-moved
        await _ensure_folder_location_available(
            game.folder_location, current_user.id, db, exclude_game_id=game_id
        )
        restore_game_from_trash(
            _DATA_ROOT / str(game.user_id) / "games" / game.folder_location, _DATA_ROOT, game_id
        )
    game.deleted_at = None
    await db.commit()
    await db.refresh(game)
    return game


# Compatibility exports for existing callers and stable OpenAPI model identities.
__all__ = [
    "ALLOWED_ASSET_KINDS",
    "AssetUrlRequest",
    "ChecklistItemUpdate",
    "ChecklistItemWrite",
    "ChecklistReorder",
    "DetectDatesRequest",
    "FIELD_CHANGE_TRACKED_FIELDS",
    "GameFileUpdate",
    "MediaItemUpdate",
    "MetadataRefreshRequest",
    "MetadataSearchResponse",
    "NoteRename",
    "NoteWrite",
    "ProfileUpdate",
    "ProfileWrite",
    "WiseOldManSyncRequest",
    "_DATA_ROOT",
    "_GAME_METADATA_FIELDS",
    "_NON_NULLABLE_UPDATE_FIELDS",
    "_NOTE_NAME_PATTERN",
    "_checklist_item_to_dict",
    "_derive_sort_title",
    "_drop_nulls_for_required_fields",
    "_duplicate_folder_error",
    "_ensure_folder_location_available",
    "_field_change_value_to_text",
    "_game_file_subdir",
    "_game_file_to_dict",
    "_game_note_path",
    "_get_game_or_404",
    "_get_profile_or_404",
    "_media_item_to_dict",
    "_metadata_value_is_present",
    "_normalize_metadata_title",
    "_normalize_note_name",
    "_note_summary",
    "_profile_to_dict",
    "_record_field_changes",
    "_record_stat_snapshot",
    "_scan_settings_to_preferences",
    "_sync_game_file_items",
    "_thumb_dir",
    "create_checklist_item",
    "create_game_note",
    "create_game_profile",
    "delete_checklist_item",
    "delete_game_file",
    "delete_game_note",
    "delete_game_profile",
    "delete_game_screenshot",
    "detect_media_dates",
    "download_game_asset",
    "get_clip_thumbnail",
    "get_game_asset",
    "get_game_file",
    "get_game_note",
    "get_game_screenshot",
    "get_profile_stat_history",
    "list_game_checklist",
    "list_game_file_trash",
    "list_game_files",
    "list_game_note_summaries",
    "list_game_notes",
    "list_game_profile_trash",
    "list_game_profiles",
    "list_game_screenshot_trash",
    "list_game_screenshots",
    "refresh_game_metadata",
    "rename_game_note",
    "reorder_checklist",
    "restore_game_file",
    "restore_game_profile",
    "restore_game_screenshot",
    "save_clip_thumbnail",
    "search_metadata",
    "sync_profile_wiseoldman",
    "update_checklist_item",
    "update_game_file",
    "update_game_note",
    "update_game_profile",
    "update_media_item",
    "upload_game_asset",
    "upload_game_files",
    "upload_game_screenshots",
]
