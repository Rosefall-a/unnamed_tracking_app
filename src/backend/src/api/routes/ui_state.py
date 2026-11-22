"""What a person last chose on a page (view modes, sorts, filters, Home picks,
collection order), stored here instead of in their browser."""

import json
import re
import time
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.models.user_ui_state import UserUiState
from src.database.session import get_db

router = APIRouter(prefix="/api/ui-state", tags=["ui-state"], dependencies=[Depends(get_current_user)])

_KEY = re.compile(r"^[A-Za-z0-9:_.\-]{1,200}$")
# a saved filter or a collection's order is a few KB; this keeps one bad write
# from filling the database
MAX_VALUE_BYTES = 512 * 1024
MAX_KEYS = 5000


def _check(key: str, value: Any) -> None:
    if not _KEY.match(key):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid name.")
    if len(json.dumps(value)) > MAX_VALUE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=f"{key} is too large to save."
        )


async def _room_for(db: AsyncSession, user_id: Any, adding: int) -> None:
    have = await db.scalar(select(func.count()).where(UserUiState.user_id == user_id)) or 0
    if have + adding > MAX_KEYS:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Too many saved choices.")


@router.get("")
async def get_ui_state(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    """Everything saved for this person, by name."""
    rows = await db.execute(
        select(UserUiState.key, UserUiState.value).where(UserUiState.user_id == current_user.id)
    )
    return dict(rows.tuples().all())


@router.put("/{key}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def put_ui_state(
    key: str,
    value: Any = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Saves one choice, replacing what was there."""
    _check(key, value)
    exists = await db.get(UserUiState, (current_user.id, key))
    if exists is None:
        await _room_for(db, current_user.id, 1)
    now = int(time.time())
    await db.execute(
        pg_insert(UserUiState)
        .values(user_id=current_user.id, key=key, value=value, updated_at=now)
        .on_conflict_do_update(
            index_elements=["user_id", "key"], set_={"value": value, "updated_at": now}
        )
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/{key}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_ui_state(
    key: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Forgets one choice, so the page goes back to its default."""
    await db.execute(
        delete(UserUiState).where(UserUiState.user_id == current_user.id, UserUiState.key == key)
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/import")
async def import_ui_state(
    values: dict[str, Any] = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, list[str]]:
    """Takes what an older version of the app kept in a browser. A name already
    saved here keeps its saved value. Returns the names now safe on the server,
    so the browser deletes only those, and the ones it could not take."""
    saved = set(
        (
            await db.execute(
                select(UserUiState.key).where(
                    UserUiState.user_id == current_user.id, UserUiState.key.in_(list(values))
                )
            )
        ).scalars()
    )
    now = int(time.time())
    stored: list[str] = []
    rejected: list[str] = []
    new_rows = []
    for key, value in values.items():
        if key in saved:
            stored.append(key)
            continue
        try:
            _check(key, value)
        except HTTPException:
            rejected.append(key)
            continue
        new_rows.append({"user_id": current_user.id, "key": key, "value": value, "updated_at": now})
        stored.append(key)
    if new_rows:
        await _room_for(db, current_user.id, len(new_rows))
        await db.execute(pg_insert(UserUiState).values(new_rows).on_conflict_do_nothing())
        await db.commit()
    return {"stored": stored, "rejected": rejected}
