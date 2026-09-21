"""In-app notifications. The bell polls `/unread-count`, which also
generates anything newly due (see features/notifications.py), so there is
no background job behind this."""

import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import get_db
from src.features.notifications import generate_for_user

router = APIRouter(
    prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(get_current_user)]
)


def _read(n: Notification) -> dict:
    return {
        "id": n.id,
        "kind": n.kind,
        "media_type": n.media_type,
        "media_id": n.media_id,
        "title": n.title,
        "body": n.body,
        "poster_url": n.poster_url,
        "event_at": n.event_at,
        "read": n.read_at is not None,
    }


@router.get("/unread-count")
async def unread_count(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    await generate_for_user(db, current_user.id)
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
    )
    return {"unread": count or 0}


@router.get("")
async def list_notifications(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    unread_only: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    await generate_for_user(db, current_user.id)
    stmt = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    rows = (
        (await db.execute(stmt.order_by(Notification.event_at.desc()).limit(limit).offset(offset)))
        .scalars()
        .all()
    )
    unread = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
    )
    return {"items": [_read(n) for n in rows], "unread": unread or 0}


@router.post("/read-all", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_all_read(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> None:
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
        .values(read_at=int(time.time()))
    )
    await db.commit()


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def mark_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(read_at=int(time.time()))
    )
    if not result.rowcount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.commit()


@router.post(
    "/{notification_id}/unread", status_code=status.HTTP_204_NO_CONTENT, response_model=None
)
async def mark_unread(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == current_user.id)
        .values(read_at=None)
    )
    if not result.rowcount:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    await db.commit()


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    await db.execute(
        delete(Notification).where(
            Notification.id == notification_id, Notification.user_id == current_user.id
        )
    )
    await db.commit()
