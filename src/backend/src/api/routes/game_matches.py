"""Review of entries that may be the same game (see features/game_matches.py)."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.game_match import GameMatch
from src.database.models.game_note_detail import GameNoteDetail
from src.database.models.media_item import MediaItem
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import get_db
from src.features import game_matches

router = APIRouter(
    prefix="/api/game-matches", tags=["game-matches"], dependencies=[Depends(get_current_user)]
)


class MergeRequest(BaseModel):
    # whose details win where both entries have one
    prefer: Literal["mine", "steam"] = "mine"


async def _summary(db: AsyncSession, game: Game) -> dict:
    achievements = await db.scalar(
        select(func.count()).select_from(Achievement).where(Achievement.game_id == game.id)
    )
    notes = await db.scalar(
        select(func.count()).select_from(GameNoteDetail).where(GameNoteDetail.game_id == game.id)
    )
    screenshots = await db.scalar(
        select(func.count())
        .select_from(MediaItem)
        .where(MediaItem.game_id == game.id, MediaItem.deleted_at.is_(None))
    )
    return {
        "id": game.id,
        "title": game.title,
        "cover_url": f"/api/game/{game.id}/assets/key_art?w=240",
        "source": game.source,
        "status": game.status.value if hasattr(game.status, "value") else str(game.status),
        "rating": float(game.rating_overall) if game.rating_overall is not None else None,
        "platform": game.platform,
        "playtime_seconds": game.playtime_seconds,
        "release_date": game.release_date.isoformat() if game.release_date else None,
        "achievements": achievements or 0,
        "notes": notes or 0,
        "screenshots": screenshots or 0,
        "deleted": game.deleted_at is not None,
    }


async def _read(db: AsyncSession, match: GameMatch) -> dict:
    original = await db.get(Game, match.original_id)
    steam_game = await db.get(Game, match.steam_id)
    return {
        "id": match.id,
        "status": match.status,
        "prefer": match.prefer,
        "created_at": match.created_at,
        "resolved_at": match.resolved_at,
        "original": await _summary(db, original) if original else None,
        "steam": await _summary(db, steam_game) if steam_game else None,
    }


async def _get_match(db: AsyncSession, match_id: UUID, user: User) -> GameMatch:
    match = await db.scalar(
        select(GameMatch).where(GameMatch.id == match_id, GameMatch.user_id == user.id)
    )
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match not found.")
    return match


async def _settle_notification(db: AsyncSession, match: GameMatch) -> None:
    """Once a pair is decided its notification has done its job."""
    note = await db.scalar(
        select(Notification).where(
            Notification.user_id == match.user_id,
            Notification.dedupe_key == f"game-match:{match.id}",
        )
    )
    if note is not None and note.read_at is None:
        from time import time

        note.read_at = int(time())


@router.get("")
async def list_matches(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    matches = (
        await db.scalars(
            select(GameMatch)
            .where(GameMatch.user_id == current_user.id)
            .order_by(GameMatch.created_at.desc())
        )
    ).all()
    items = [await _read(db, m) for m in matches]
    return {
        "items": [i for i in items if i["original"] and i["steam"]],
        "pending": sum(1 for m in matches if m.status == "pending"),
    }


@router.get("/for/{game_id}")
async def matches_for_game(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """The undecided pairs a game is in, for the notice on its page."""
    matches = (
        await db.scalars(
            select(GameMatch).where(
                GameMatch.user_id == current_user.id,
                GameMatch.status == "pending",
                or_(GameMatch.original_id == game_id, GameMatch.steam_id == game_id),
            )
        )
    ).all()
    return [await _read(db, m) for m in matches]


@router.post("/scan")
async def scan(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Look through the whole library for pairs that may be one game."""
    found = await game_matches.find_matches(db, current_user.id)
    await db.commit()
    return {"found": found}


@router.post("/{match_id}/merge")
async def merge_match(
    match_id: UUID,
    payload: MergeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    match = await _get_match(db, match_id, current_user)
    if match.status == "merged":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already merged.")
    try:
        await game_matches.merge(db, match, payload.prefer)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    await _settle_notification(db, match)
    await db.commit()
    return await _read(db, match)


@router.post("/{match_id}/keep-both")
async def keep_both(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    match = await _get_match(db, match_id, current_user)
    if match.status == "merged":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Undo the merge before keeping both."
        )
    game_matches.keep_both(match)
    await _settle_notification(db, match)
    await db.commit()
    return await _read(db, match)


@router.post("/{match_id}/reopen")
async def reopen(
    match_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Change a decision: undo a merge, or ask again about a pair kept separate."""
    match = await _get_match(db, match_id, current_user)
    if match.status == "merged":
        try:
            await game_matches.undo_merge(db, match)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    else:
        match.status = "pending"
        match.resolved_at = None
    await db.commit()
    return await _read(db, match)
