from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.game import Game
from src.database.models.game_afk_time import GameAfkTime
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/game", tags=["game"])


class AfkTimeWrite(BaseModel):
    seconds: int = Field(gt=0, le=86_400)


@router.get("/playnite/{playnite_guid}")
async def find_game_by_playnite_guid(
    playnite_guid: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, str]:
    """Resolve a user's Playnite GUID to the corresponding game id."""
    game_id = await db.scalar(
        select(Game.id).where(
            Game.playnite_guid == playnite_guid,
            Game.user_id == current_user.id,
            Game.deleted_at.is_(None),
        )
    )
    if game_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")
    return {"game_id": str(game_id)}


@router.get("/{game_id}/afk")
async def get_game_afk_time(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    """Return the total AFK time recorded for a game."""
    game_exists = await db.scalar(
        select(Game.id).where(
            Game.id == game_id,
            Game.user_id == current_user.id,
            Game.deleted_at.is_(None),
        )
    )
    if game_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    total = await db.scalar(select(GameAfkTime.afk_seconds).where(GameAfkTime.game_id == game_id))
    return {"game_id": str(game_id), "afk_seconds": total or 0}


@router.post("/{game_id}/afk", status_code=200)
async def add_game_afk_time(
    game_id: UUID,
    payload: AfkTimeWrite,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, int | str]:
    """Atomically add newly observed AFK time to a game."""
    game_exists = await db.scalar(
        select(Game.id).where(
            Game.id == game_id,
            Game.user_id == current_user.id,
            Game.deleted_at.is_(None),
        )
    )
    if game_exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Game not found")

    statement = insert(GameAfkTime).values(game_id=game_id, afk_seconds=payload.seconds)
    statement = statement.on_conflict_do_update(
        index_elements=[GameAfkTime.game_id],
        set_={"afk_seconds": GameAfkTime.afk_seconds + payload.seconds},
    )
    statement = statement.returning(GameAfkTime.afk_seconds)
    total = (await db.execute(statement)).scalar_one()
    await db.commit()
    return {"game_id": str(game_id), "afk_seconds": total}
