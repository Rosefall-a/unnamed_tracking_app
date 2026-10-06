"""Game checklists routes, composed by the games router."""

import time
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.game_profiles import _get_profile_or_404
from src.api.routes.utils.games import (
    _get_game_or_404,
)
from src.core.auth import get_current_user
from src.database.models.game_checklist_item import GameChecklistItem
from src.database.models.user import User
from src.database.session import get_db

_UNSCOPED_ONLY_DEFAULT = Query(False, description="Only items with no profile_id set.")


_DB_DEPENDENCY = Depends(get_db)


_CURRENT_USER_DEPENDENCY = Depends(get_current_user)


_NONE_FORM = Form(None)


router = APIRouter()


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
    __module__ = "src.api.routes.games"
    text: str
    profile_id: UUID | None = None
    is_header: bool = False


class ChecklistItemUpdate(BaseModel):
    __module__ = "src.api.routes.games"
    text: str | None = None
    done: bool | None = None
    is_header: bool | None = None
    sort_order: float | None = None


@router.get("/{game_id}/checklist")
async def list_game_checklist(
    game_id: UUID,
    profile_id: UUID | None = _NONE_FORM,
    unscoped_only: bool = _UNSCOPED_ONLY_DEFAULT,
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
    __module__ = "src.api.routes.games"
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
