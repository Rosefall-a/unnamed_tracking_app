"""API routes for managing screenshot tags.

Tags are scoped to a user, not a single game or screenshot — one tag can be
reused across every screenshot that user owns. Renaming or deleting a tag
here applies everywhere it's attached.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.screenshot import (
    ScreenshotTagRead,
    ScreenshotTagUpdate,
    ScreenshotTagWithCount,
)
from src.core.auth import get_current_user
from src.database.models.game import ScreenshotTag, screenshot_tag_links
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(
    prefix="/api/screenshot-tags",
    tags=["screenshot-tags"],
    dependencies=[Depends(get_current_user)],
)


async def _get_tag_or_404(tag_id: UUID, db: AsyncSession, user_id: UUID) -> ScreenshotTag:
    tag = await db.scalar(
        select(ScreenshotTag).where(ScreenshotTag.id == tag_id, ScreenshotTag.user_id == user_id)
    )
    if tag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Tag {tag_id} not found")
    return tag


def _duplicate_tag_error(name: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "error": "duplicate_tag_name",
            "field": "name",
            "value": name,
            "message": f"You already have a tag named '{name}'.",
        },
    )


@router.get("", response_model=list[ScreenshotTagWithCount])
async def list_tags(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[ScreenshotTagWithCount]:
    """List every screenshot tag for the current user, with how many screenshots use each."""
    stmt = (
        select(ScreenshotTag, func.count(screenshot_tag_links.c.screenshot_id))
        .outerjoin(screenshot_tag_links, screenshot_tag_links.c.tag_id == ScreenshotTag.id)
        .where(ScreenshotTag.user_id == current_user.id)
        .group_by(ScreenshotTag.id)
        .order_by(ScreenshotTag.name)
    )
    result = await db.execute(stmt)
    return [
        ScreenshotTagWithCount(id=tag.id, name=tag.name, screenshot_count=count)
        for tag, count in result.all()
    ]


@router.patch("/{tag_id}", response_model=ScreenshotTagRead)
async def rename_tag(
    tag_id: UUID,
    payload: ScreenshotTagUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ScreenshotTag:
    """Rename a tag. Applies to every screenshot it's currently attached to."""
    tag = await _get_tag_or_404(tag_id, db, current_user.id)
    tag.name = payload.name.strip()

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise _duplicate_tag_error(payload.name.strip()) from exc

    await db.refresh(tag)
    return tag


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_tag(
    tag_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a tag, detaching it from any screenshots that used it."""
    tag = await _get_tag_or_404(tag_id, db, current_user.id)
    await db.delete(tag)
    await db.commit()
