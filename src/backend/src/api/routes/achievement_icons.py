"""Local copies of achievement and trophy icons."""

import asyncio
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.image_prefetch import ICON_ROOT
from src.helpers.remote_images import RemoteImageError, fetch_icon, icon_cache_path, make_large_icon

router = APIRouter(
    prefix="/api/achievement-icon",
    tags=["games"],
    dependencies=[Depends(get_current_user)],
)

_ICON_ROOT = ICON_ROOT


@router.get("/{achievement_id}")
async def get_achievement_icon(
    achievement_id: UUID,
    large: bool = Query(default=False),
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
            await asyncio.to_thread(fetch_icon, url, target)
        except RemoteImageError:
            return RedirectResponse(
                url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Cache-Control": "no-store"},
            )
    if large:
        # the bigger copy for the achievement's own page, made once from the small one
        big = icon_cache_path(_ICON_ROOT, url, large=True)
        if not big.is_file():
            await asyncio.to_thread(make_large_icon, target, big)
        target = big
    return FileResponse(
        target,
        media_type="image/png",
        headers={"Cache-Control": "private, max-age=86400"},
    )
