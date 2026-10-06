"""Game profiles routes, composed by the games router."""

import asyncio
import time
from uuid import UUID

from fastapi import (
    APIRouter,
    Body,
    Depends,
    HTTPException,
    status,
)
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.utils.games import (
    _get_game_or_404,
)
from src.core.auth import get_current_user
from src.database.models.game_profile import GameProfile
from src.database.models.game_profile_stat_snapshot import GameProfileStatSnapshot
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games import wiseoldman
from src.features.trash.sweep import RETENTION_SECONDS

_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


router = APIRouter()


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


# Keep the established workflow and public parameters together.
# pylint: disable=too-many-positional-arguments
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


# pylint: enable=too-many-positional-arguments


class ProfileWrite(BaseModel):
    __module__ = "src.api.routes.games"
    name: str


class ProfileUpdate(BaseModel):
    __module__ = "src.api.routes.games"
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
    __module__ = "src.api.routes.games"
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
        except Exception:  # pylint: disable=broad-exception-caught
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
