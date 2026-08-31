import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.game import Game, GameStatus
from app.api.schemas.game import GameCreate, GameRead, GameUpdate

router = APIRouter(
    prefix="/api/game",
    tags=["game"],
)

_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


def _derive_sort_title(title: str) -> str:
    """'The Witcher 3' -> 'witcher 3' so articles don't affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


async def _get_game_or_404(game_id: UUID, db: AsyncSession) -> Game:
    game = await db.get(Game, game_id)
    if game is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Game {game_id} not found",
        )
    return game


@router.post("/create", response_model=GameRead, status_code=status.HTTP_201_CREATED)
async def create_game(payload: GameCreate, db: AsyncSession = Depends(get_db)) -> Game:
    data = payload.model_dump()
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])

    game = Game(**data)
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return game


@router.get("/list", response_model=list[GameRead])
async def list_games(
    db: AsyncSession = Depends(get_db),
    status_filter: GameStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Game]:
    stmt = select(Game)

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
async def get_game(game_id: UUID, db: AsyncSession = Depends(get_db)) -> Game:
    return await _get_game_or_404(game_id, db)


@router.patch("/update/{game_id}", response_model=GameRead)
async def update_game(
    game_id: UUID, payload: GameUpdate, db: AsyncSession = Depends(get_db)
) -> Game:
    game = await _get_game_or_404(game_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(game, field, value)

    # Keep sort_title in sync if title changed but sort_title wasn't explicitly set
    if "title" in updates and "sort_title" not in updates:
        game.sort_title = _derive_sort_title(game.title)

    await db.commit()
    await db.refresh(game)
    return game


@router.delete("/delete/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_game(game_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    game = await _get_game_or_404(game_id, db)
    await db.delete(game)
    await db.commit()