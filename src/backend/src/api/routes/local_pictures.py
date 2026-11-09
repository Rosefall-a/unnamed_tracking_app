"""Local copies of episode stills and of the pictures and clips inside game
descriptions, so those pages show with no internet. The first request saves a
copy if saving the row did not already; when the site cannot be reached the
browser is sent to the original address. Only an address that really is on one
of your own episodes or games is ever fetched, so these cannot be used to make
the server download anything else."""

import asyncio
import mimetypes
from collections.abc import Callable
from pathlib import Path
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.game import Game
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow
from src.database.models.user import User
from src.database.session import get_db
from src.helpers import image_prefetch
from src.helpers.local_copies import (
    cache_root,
    description_file_path,
    description_files,
    fetch_description_file,
    fetch_still,
    still_path,
)
from src.helpers.remote_images import RemoteImageError

# not every Python knows these two, and a wrong type stops the picture showing
mimetypes.add_type("image/avif", ".avif")
mimetypes.add_type("image/webp", ".webp")

router = APIRouter(prefix="/api", tags=["media"], dependencies=[Depends(get_current_user)])

_NOT_FOUND = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such picture.")


async def _serve(url: str, target: Path, fetch: Callable[[str, Path], None]) -> Response:
    if not target.is_file():
        try:
            await asyncio.to_thread(fetch, url, target)
        except (RemoteImageError, OSError):
            return RedirectResponse(
                url,
                status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                headers={"Cache-Control": "no-store"},
            )
    kind = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    return FileResponse(
        target, media_type=kind, headers={"Cache-Control": "private, max-age=86400"}
    )


@router.get("/episode-still/{media_type}/{episode_id}")
async def get_episode_still(
    media_type: Literal["tv", "anime"],
    episode_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    if media_type == "tv":
        query = (
            select(TVEpisode.still_url)
            .join(TVSeason, TVSeason.id == TVEpisode.season_id)
            .join(TVShow, TVShow.id == TVSeason.show_id)
            .where(TVEpisode.id == episode_id, TVShow.user_id == current_user.id)
        )
    else:
        query = (
            select(AnimeEpisode.still_url)
            .join(AnimeSeason, AnimeSeason.id == AnimeEpisode.season_id)
            .join(Anime, Anime.id == AnimeSeason.show_id)
            .where(AnimeEpisode.id == episode_id, Anime.user_id == current_user.id)
        )
    url = await db.scalar(query)
    if not url or not url.startswith(("http://", "https://")):
        raise _NOT_FOUND
    root = cache_root(image_prefetch.MEDIA_ROOT, current_user.id)
    return await _serve(url, still_path(root, url), fetch_still)


@router.get("/game/{game_id}/page-file")
async def get_description_file(
    game_id: UUID,
    u: str = Query(..., max_length=2048),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    description = await db.scalar(
        select(Game.description).where(Game.id == game_id, Game.user_id == current_user.id)
    )
    if u not in description_files(description):
        raise _NOT_FOUND
    root = cache_root(image_prefetch.MEDIA_ROOT, current_user.id)
    return await _serve(u, description_file_path(root, u), fetch_description_file)
