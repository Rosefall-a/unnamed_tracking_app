"""Game profile API routes."""

import asyncio
import time
from uuid import UUID

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.game import GameBulkUpdate, GameCreate, GameFieldChangeRead, GameRead, GameUpdate
from src.core.auth import get_current_user
from src.core.config import settings
from src.database.models.game import Game, GameLink, GameStatus
from src.database.models.game_checklist_item import GameChecklistItem
from src.database.models.game_field_change import GameFieldChange
from src.database.models.game_profile import GameProfile
from src.database.models.game_profile_stat_snapshot import GameProfileStatSnapshot
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import wiseoldman
from src.features.trash.game_trash import move_game_to_trash, restore_game_from_trash
from src.features.trash.media_trash import move_media_file_to_trash, restore_media_file_from_trash
from src.features.trash.sweep import RETENTION_SECONDS
from src.helpers.media import media_subdir, save_media_bytes
from src.helpers.save_game_asset import create_game_folder
from src.api.routes.game_helpers import _DATA_ROOT, _get_game_or_404


router = APIRouter()
_DB_DEPENDENCY = Depends(get_db)
_CURRENT_USER_DEPENDENCY = Depends(get_current_user)

async def _get_profile_or_404(
    profile_id: UUID, game_id: UUID, db: AsyncSession, include_deleted: bool = False
) -> GameProfile:
    stmt = select(GameProfile).where(GameProfile.id == profile_id, GameProfile.game_id == game_id)
    if not include_deleted:
        stmt = stmt.where(GameProfile.deleted_at.is_(None))
    profile = await db.scalar(stmt)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found.")
    return profile


def _profile_to_dict(profile: GameProfile) -> dict:
    return {
        "id": str(profile.id),
        "game_id": str(profile.game_id),
        "name": profile.name,
        "note": profile.note,
        "stats": profile.stats,
        "wiseoldman_username": profile.wiseoldman_username,
        "created_at": profile.created_at,
    }


async def _record_stat_snapshot(
    db: AsyncSession,
    profile_id: UUID,
    stats: dict[str, str],
    recorded_at: int | None = None,
    xp: dict[str, int] | None = None,
    kc: dict[str, int] | None = None,
) -> None:
    """Called whenever a profile's stats change (manual edit or WiseOldMan
    sync) — a dated copy so progression can be shown later instead of only
    ever seeing the current numbers. xp/kc (WiseOldMan syncs only — a
    manual edit leaves them empty) are the raw integers a "gained this
    much" digest needs; `stats` alone (display strings) isn't precise
    enough since a level can span tens of thousands of XP. Not deduped:
    two saves the same minute just make two rows, which is harmless and
    keeps this simple."""
    if not stats:
        return
    db.add(
        GameProfileStatSnapshot(
            profile_id=profile_id,
            stats=stats,
            xp=xp or {},
            kc=kc or {},
            recorded_at=recorded_at or int(time.time()),
        )
    )


class ProfileWrite(BaseModel):
    name: str


class ProfileUpdate(BaseModel):
    name: str | None = None
    note: str | None = None
    stats: dict[str, str] | None = None
    wiseoldman_username: str | None = None


@router.get("/{game_id}/profiles")
async def list_game_profiles(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    """Named sub-scopes for a game (e.g. separate OSRS accounts) — lets
    checklist items and screenshots be filtered down to one instead of
    mixed together across every account the game has."""
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(GameProfile)
        .where(GameProfile.game_id == game_id, GameProfile.deleted_at.is_(None))
        .order_by(GameProfile.created_at.asc())
    )
    return {"profiles": [_profile_to_dict(p) for p in result.scalars().all()]}


@router.post("/{game_id}/profiles", status_code=status.HTTP_201_CREATED)
async def create_game_profile(
    game_id: UUID,
    payload: ProfileWrite,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required.")
    profile = GameProfile(game_id=game_id, name=name)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return _profile_to_dict(profile)


@router.patch("/{game_id}/profiles/{profile_id}")
async def update_game_profile(
    game_id: UUID,
    profile_id: UUID,
    payload: ProfileUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    profile = await _get_profile_or_404(profile_id, game_id, db)
    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        name = (updates["name"] or "").strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="name is required.")
        updates["name"] = name
    for field, value in updates.items():
        setattr(profile, field, value)
    if "stats" in updates:
        await _record_stat_snapshot(db, profile.id, updates["stats"])
    await db.commit()
    await db.refresh(profile)
    return _profile_to_dict(profile)


class WiseOldManSyncRequest(BaseModel):
    username: str | None = None


_WISEOLDMAN_SYNC_BODY = Body(default=WiseOldManSyncRequest())


@router.post("/{game_id}/profiles/{profile_id}/sync-wiseoldman")
async def sync_profile_wiseoldman(
    game_id: UUID,
    profile_id: UUID,
    payload: WiseOldManSyncRequest = _WISEOLDMAN_SYNC_BODY,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    """Pulls current skill levels from wiseoldman.net (OSRS's community
    stat tracker, no account/API key needed) into this profile's stats.
    Manual, click-to-sync — no scheduled background refresh."""
    await _get_game_or_404(game_id, db, current_user.id)
    profile = await _get_profile_or_404(profile_id, game_id, db)
    username = (payload.username or profile.wiseoldman_username or "").strip()
    if not username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="A WiseOldMan username is required."
        )
    try:
        result = await asyncio.to_thread(wiseoldman.get_player_stats, username)
    except wiseoldman.WiseOldManError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    stats = dict(result["stats"])
    if result.get("combat_level"):
        stats["Combat"] = result["combat_level"]
    profile.stats = stats
    profile.wiseoldman_username = username

    # first sync ever for this profile — backfill whatever history
    # WiseOldMan already has for the account (only as good as how often
    # *someone* updated it there before), so progression doesn't start
    # from a blank slate just because this is the first time this app
    # asked. A later sync only ever adds today's snapshot below.
    has_history = await db.scalar(
        select(GameProfileStatSnapshot.id)
        .where(GameProfileStatSnapshot.profile_id == profile.id)
        .limit(1)
    )
    if has_history is None:
        try:
            history = await asyncio.to_thread(wiseoldman.get_player_snapshots, username)
        except Exception:  # noqa: BLE001 — backfill is best-effort, never blocks the sync itself
            history = []
        for entry in history:
            await _record_stat_snapshot(
                db,
                profile.id,
                entry["stats"],
                entry["recorded_at"],
                entry.get("xp"),
                entry.get("kc"),
            )

    await _record_stat_snapshot(db, profile.id, stats, xp=result.get("xp"), kc=result.get("kc"))
    await db.commit()
    await db.refresh(profile)
    return _profile_to_dict(profile)


@router.get("/{game_id}/profiles/{profile_id}/stat-history")
async def get_profile_stat_history(
    game_id: UUID,
    profile_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    await _get_profile_or_404(profile_id, game_id, db)
    result = await db.execute(
        select(GameProfileStatSnapshot)
        .where(GameProfileStatSnapshot.profile_id == profile_id)
        .order_by(GameProfileStatSnapshot.recorded_at.desc())
    )
    return {
        "snapshots": [
            {
                "id": str(s.id),
                "recorded_at": s.recorded_at,
                "stats": s.stats,
                "xp": s.xp,
                "kc": s.kc,
            }
            for s in result.scalars().all()
        ]
    }


@router.delete("/{game_id}/profiles/{profile_id}")
async def delete_game_profile(
    game_id: UUID,
    profile_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    """Soft-delete only — no files involved, so this just flips the flag
    (features/trash/sweep.py purges the row itself after 7 days). Checklist
    items and media tagged to this profile keep their profile_id and
    simply stop showing up under an active profile filter until restored."""
    await _get_game_or_404(game_id, db, current_user.id)
    profile = await _get_profile_or_404(profile_id, game_id, db)
    profile.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "id": str(profile_id)}


@router.get("/{game_id}/profiles/trash")
async def list_game_profile_trash(
    game_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(GameProfile).where(
            GameProfile.game_id == game_id, GameProfile.deleted_at.is_not(None)
        )
    )
    profiles = []
    for p in result.scalars().all():
        assert p.deleted_at is not None  # guaranteed by the deleted_at.is_not(None) filter above
        profiles.append(
            {
                **_profile_to_dict(p),
                "deleted_at": p.deleted_at,
                "purge_at": p.deleted_at + RETENTION_SECONDS,
            }
        )
    return {"profiles": profiles}


@router.post("/{game_id}/profiles/{profile_id}/restore")
async def restore_game_profile(
    game_id: UUID,
    profile_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    profile = await _get_profile_or_404(profile_id, game_id, db, include_deleted=True)
    if profile.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Profile is not trashed."
        )
    profile.deleted_at = None
    await db.commit()
    await db.refresh(profile)
    return _profile_to_dict(profile)


def _checklist_item_to_dict(item: GameChecklistItem) -> dict:
    return {
        "id": str(item.id),
        "game_id": str(item.game_id),
        "profile_id": str(item.profile_id) if item.profile_id else None,
        "text": item.text,
        "done": item.done,
        "is_header": item.is_header,
        "sort_order": item.sort_order,
        "created_at": item.created_at,
    }


class ChecklistItemWrite(BaseModel):
    text: str
    profile_id: UUID | None = None
    is_header: bool = False


class ChecklistItemUpdate(BaseModel):
    text: str | None = None
    done: bool | None = None
    is_header: bool | None = None
    sort_order: float | None = None


@router.get("/{game_id}/checklist")
async def list_game_checklist(
    game_id: UUID,
    profile_id: UUID | None = _NONE_FORM,
    unscoped_only: bool = Query(False, description="Only items with no profile_id set."),
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, list[dict]]:
    await _get_game_or_404(game_id, db, current_user.id)
    stmt = select(GameChecklistItem).where(
        GameChecklistItem.game_id == game_id, GameChecklistItem.deleted_at.is_(None)
    )
    if profile_id is not None:
        stmt = stmt.where(GameChecklistItem.profile_id == profile_id)
    elif unscoped_only:
        stmt = stmt.where(GameChecklistItem.profile_id.is_(None))
    result = await db.execute(
        stmt.order_by(GameChecklistItem.sort_order.asc(), GameChecklistItem.created_at.asc())
    )
    return {"items": [_checklist_item_to_dict(item) for item in result.scalars().all()]}


@router.post("/{game_id}/checklist", status_code=status.HTTP_201_CREATED)
async def create_checklist_item(
    game_id: UUID,
    payload: ChecklistItemWrite,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="text is required.")
    if payload.profile_id is not None:
        await _get_profile_or_404(payload.profile_id, game_id, db)
    max_sort = await db.scalar(
        select(func.max(GameChecklistItem.sort_order)).where(
            GameChecklistItem.game_id == game_id, GameChecklistItem.profile_id == payload.profile_id
        )
    )
    item = GameChecklistItem(
        game_id=game_id,
        profile_id=payload.profile_id,
        text=text,
        is_header=payload.is_header,
        sort_order=(max_sort or 0) + 1,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _checklist_item_to_dict(item)


class ChecklistReorder(BaseModel):
    # the full ordered list of item ids within one scope (profile_id must
    # match what they were fetched/created under) — sent whole rather than
    # as a single move, so an up/down-arrow swap and a future drag-and-drop
    # both reduce to "here's the new order" instead of two different APIs
    profile_id: UUID | None = None
    item_ids: list[UUID]


@router.put("/{game_id}/checklist/reorder")
async def reorder_checklist(
    game_id: UUID,
    payload: ChecklistReorder,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    await _get_game_or_404(game_id, db, current_user.id)
    result = await db.execute(
        select(GameChecklistItem).where(
            GameChecklistItem.game_id == game_id,
            GameChecklistItem.profile_id == payload.profile_id,
            GameChecklistItem.deleted_at.is_(None),
        )
    )
    items_by_id = {item.id: item for item in result.scalars().all()}
    for index, item_id in enumerate(payload.item_ids):
        item = items_by_id.get(item_id)
        if item is not None:
            item.sort_order = float(index)
    await db.commit()
    return {"status": "reordered"}


@router.patch("/{game_id}/checklist/{item_id}")
async def update_checklist_item(
    game_id: UUID,
    item_id: UUID,
    payload: ChecklistItemUpdate,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict:
    await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(GameChecklistItem).where(
            GameChecklistItem.id == item_id,
            GameChecklistItem.game_id == game_id,
            GameChecklistItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found."
        )
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    await db.commit()
    await db.refresh(item)
    return _checklist_item_to_dict(item)


@router.delete("/{game_id}/checklist/{item_id}")
async def delete_checklist_item(
    game_id: UUID,
    item_id: UUID,
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
) -> dict[str, str]:
    await _get_game_or_404(game_id, db, current_user.id)
    item = await db.scalar(
        select(GameChecklistItem).where(
            GameChecklistItem.id == item_id,
            GameChecklistItem.game_id == game_id,
            GameChecklistItem.deleted_at.is_(None),
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Checklist item not found."
        )
    item.deleted_at = int(time.time())
    await db.commit()
    return {"status": "trashed", "id": str(item_id)}


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


@router.get("/list", response_model=list[GameRead])
async def list_games(
    db: AsyncSession = _DB_DEPENDENCY,
    current_user: User = _CURRENT_USER_DEPENDENCY,
    status_filter: GameStatus | None = _NONE_QUERY_STATUS,
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
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
