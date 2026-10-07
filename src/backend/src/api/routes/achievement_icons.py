"""Local copies of achievement and trophy icons."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.image_prefetch import ICON_ROOT, WIDTHS
from src.helpers.remote_images import RemoteImageError, fetch_and_store, icon_cache_path

router = APIRouter(
    prefix="/api/achievement-icon",
    tags=["games"],
    dependencies=[Depends(get_current_user)],
)

_ICON_ROOT = ICON_ROOT


@router.get("/{achievement_id}")
async def get_achievement_icon(
    achievement_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """The icon from this server's own disk, downloaded the first time it is
    needed if saving the achievement did not already. If the download fails the
    browser is sent to the original address."""
    url = await db.scalar(
        select(Achievement.icon_url)
        .join(Game, Game.id == Achievement.game_id)
        .where(Achievement.id == achievement_id, Game.user_id == current_user.id)
    )
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such icon.")
    target = icon_cache_path(_ICON_ROOT, url)
    if not target.is_file():
        try:
            await asyncio.to_thread(fetch_and_store, url, target, WIDTHS["icon"])
        except RemoteImageError:
            return RedirectResponse(
                url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Cache-Control": "no-store"},
            )
    return FileResponse(
        target,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=86400"},
    )
