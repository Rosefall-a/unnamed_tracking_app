"""Local copies of the posters and backdrops of movies, TV shows and anime."""

import asyncio
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.anime import Anime
from src.database.models.movies import Movie
from src.database.models.tv_show import TVShow
from src.database.models.user import User
from src.database.session import get_db
from src.helpers.image_prefetch import MEDIA_ROOT, WIDTHS
from src.helpers.remote_images import RemoteImageError, cache_path, fetch_and_store

router = APIRouter(
    prefix="/api/media-image",
    tags=["media"],
    dependencies=[Depends(get_current_user)],
)

_DATA_ROOT = MEDIA_ROOT
_MODELS: dict[str, Any] = {"movie": Movie, "tv": TVShow, "anime": Anime}


@router.get("/{media_type}/{item_id}/{which}")
async def get_media_image(
    media_type: Literal["movie", "tv", "anime"],
    item_id: UUID,
    which: Literal["poster", "backdrop", "hero"],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """The title's poster or backdrop from this server's own disk, downloading
    and shrinking it the first time. If the download fails the browser is sent
    to the original address instead, so a picture never just goes missing."""
    model = _MODELS[media_type]
    row = await db.scalar(
        select(model).where(model.id == item_id, model.user_id == current_user.id)
    )
    url: str | None = None
    if row:
        # "hero" is the picture behind a page's title: the backdrop, or the poster
        # when the title has no backdrop
        url = (
            (row.backdrop_url or row.poster_url)
            if which == "hero"
            else getattr(row, f"{which}_url", None)
        )
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such image.")

    # the hero of a title with a backdrop is that same picture: one file, not two
    name = "backdrop" if which == "hero" and row.backdrop_url else which
    target = cache_path(_DATA_ROOT / str(current_user.id) / ".cache", media_type, str(item_id), name, url)
    if not target.is_file():
        try:
            await asyncio.to_thread(fetch_and_store, url, target, WIDTHS[which])
        except RemoteImageError:
            return RedirectResponse(
                url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Cache-Control": "no-store"},
            )
    return FileResponse(
        target,
        media_type="image/jpeg",
        headers={"Cache-Control": "private, max-age=3600, must-revalidate"},
    )
