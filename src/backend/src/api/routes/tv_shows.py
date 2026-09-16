"""API routes for managing TV shows and their seasons."""

import asyncio
import re
import time
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.tv_show import (
    EpisodeUpdate,
    SeasonCreate,
    SeasonUpdate,
    TVShowCreate,
    TVShowRead,
    TVShowUpdate,
)
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.crypto import decrypt_secret
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow, TVShowStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.locked_fields import apply_updates_with_locking
from src.features.metadata.movies.tmdb import TMDBClient
from src.features.metadata.tv.episode_sync import fetch_season_episodes
from src.features.metadata.tv.search import search_tv_metadata
from src.features.metadata.tv.tvdb import TVDBClient

router = APIRouter(prefix="/api/tv", tags=["tv"], dependencies=[Depends(get_current_user)])

# fields the metadata search's "Apply" button can fill in — the only ones
# worth locking, since nothing else is ever set by that flow
_LOCKABLE_FIELDS = frozenset(
    {
        "title",
        "description",
        "first_air_date",
        "episode_runtime_minutes",
        "creators",
        "genres",
        "poster_url",
        "backdrop_url",
        "tmdb_score",
    }
)


class TVMetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    provider_errors: list[str] = []
    results: list[dict]


_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


def _derive_sort_title(title: str) -> str:
    """'The Wire' -> 'wire' so articles do not affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


async def _get_show_or_404(
    show_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> TVShow:
    # populate_existing: a show already in this session's identity map
    # (e.g. loaded earlier in the same request, before a season was just
    # added to it) would otherwise keep its stale, already-cached
    # `seasons` collection instead of picking up the new row
    stmt = (
        select(TVShow)
        .where(TVShow.id == show_id, TVShow.user_id == user_id)
        .execution_options(populate_existing=True)
    )
    if not include_deleted:
        stmt = stmt.where(TVShow.deleted_at.is_(None))
    show = await db.scalar(stmt)
    if show is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Show {show_id} not found")
    return show


async def _get_season_or_404(season_id: UUID, show_id: UUID, db: AsyncSession) -> TVSeason:
    season = await db.scalar(
        select(TVSeason).where(TVSeason.id == season_id, TVSeason.show_id == show_id)
    )
    if season is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Season {season_id} not found")
    return season


@router.get("/metadata/search", response_model=TVMetadataSearchResponse)
async def search_metadata(
    query: str = Query(..., min_length=2, max_length=100),
    limit: int = Query(default=8, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Search TMDB and OMDb for data that can prefill a new show,
    including its full season list where TMDB has it."""
    del current_user
    app_integrations = await get_or_create_app_integration_settings(db)
    try:
        result = await asyncio.to_thread(
            search_tv_metadata,
            query.strip(),
            limit,
            decrypt_secret(app_integrations.tmdb_api_key)
            if app_integrations.tmdb_api_key
            else None,
            decrypt_secret(app_integrations.omdb_api_key)
            if app_integrations.omdb_api_key
            else None,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc
    return result


@router.post("/create", response_model=TVShowRead, status_code=status.HTTP_201_CREATED)
async def create_show(
    payload: TVShowCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    """Create a show, optionally bulk-creating its seasons in the same
    transaction if the caller already has a season list (e.g. from a
    metadata search result)."""
    data = payload.model_dump(exclude={"seasons"})
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])

    show = TVShow(**data, user_id=current_user.id)
    db.add(show)
    await db.flush()

    for season_input in payload.seasons:
        db.add(TVSeason(**season_input.model_dump(), show_id=show.id))

    await db.commit()
    return await _get_show_or_404(show.id, db, current_user.id)


@router.get("/list", response_model=list[TVShowRead])
async def list_shows(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: TVShowStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[TVShow]:
    """Return the current user's shows, filtered by status, favorite flag, or title search."""
    stmt = select(TVShow).where(TVShow.user_id == current_user.id, TVShow.deleted_at.is_(None))

    if status_filter is not None:
        stmt = stmt.where(TVShow.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(TVShow.favorite == favorite)
    if search:
        stmt = stmt.where(TVShow.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(TVShow.sort_title).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().unique().all())


@router.get("/get/{show_id}", response_model=TVShowRead)
async def get_show(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    """Return one show by ID, with its seasons."""
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/update/{show_id}", response_model=TVShowRead)
async def update_show(
    show_id: UUID,
    payload: TVShowUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    """Update a show and keep its derived sort title synchronized."""
    show = await _get_show_or_404(show_id, db, current_user.id)

    updates = payload.model_dump(exclude_unset=True)

    apply_updates_with_locking(show, updates, _LOCKABLE_FIELDS)

    if "title" in updates and "sort_title" not in updates:
        show.sort_title = _derive_sort_title(show.title)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/delete/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_show(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete a show by ID (its seasons stay attached, hidden along with it)."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    show.deleted_at = int(time.time())
    await db.commit()


@router.post("/{show_id}/seasons", response_model=TVShowRead, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: UUID,
    payload: SeasonCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    show = await _get_show_or_404(show_id, db, current_user.id)
    db.add(TVSeason(**payload.model_dump(), show_id=show.id))
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}", response_model=TVShowRead)
async def update_season(
    show_id: UUID,
    season_id: UUID,
    payload: SeasonUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(season, field, value)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/{show_id}/seasons/{season_id}", response_model=TVShowRead)
async def delete_season(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    await db.delete(season)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


async def _get_episode_or_404(episode_id: UUID, season_id: UUID, db: AsyncSession) -> TVEpisode:
    episode = await db.scalar(
        select(TVEpisode).where(TVEpisode.id == episode_id, TVEpisode.season_id == season_id)
    )
    if episode is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Episode {episode_id} not found")
    return episode


@router.get("/{show_id}/seasons/{season_id}/episodes", response_model=TVShowRead)
async def list_episodes(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    """Return the season's episodes, syncing them in from TVmaze on the
    very first request (nothing to sync from if the show has no
    `external_id` — it wasn't found via TVmaze, e.g. added by hand).
    Every later call reads straight from the table instead of
    re-fetching."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    if not season.episodes and show.external_id:
        all_episodes, errors = await fetch_season_episodes(
            show.external_id, season.season_number
        )
        if not all_episodes and errors:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not sync episodes: {'; '.join(errors)}",
            )
        for entry in all_episodes:
            raw_air_date = entry.get("air_date")
            db.add(
                TVEpisode(
                    season_id=season.id,
                    episode_number=entry["episode_number"],
                    title=entry.get("title"),
                    description=entry.get("description"),
                    air_date=date.fromisoformat(raw_air_date) if raw_air_date else None,
                    runtime_minutes=entry.get("runtime_minutes"),
                    still_url=entry.get("still_url"),
                )
            )
        await db.commit()

    return await _get_show_or_404(show_id, db, current_user.id)


@router.patch("/{show_id}/seasons/{season_id}/episodes/{episode_id}", response_model=TVShowRead)
async def update_episode(
    show_id: UUID,
    season_id: UUID,
    episode_id: UUID,
    payload: EpisodeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TVShow:
    await _get_show_or_404(show_id, db, current_user.id)
    await _get_season_or_404(season_id, show_id, db)
    episode = await _get_episode_or_404(episode_id, season_id, db)

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(episode, field, value)

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.get("/{show_id}/relations")
async def get_show_relations(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """TheTVDB is the only real franchise/relations source for TV shows —
    TMDB has no collection concept outside of movies. Requires its own
    API key (Settings > Metadata Sources); returns an empty, clearly
    unconfigured result rather than an error when it's not set up yet."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    app_integrations = await get_or_create_app_integration_settings(db)
    if not app_integrations.tvdb_api_key:
        return {"listName": None, "related": [], "configured": False}
    tvdb_api_key = decrypt_secret(app_integrations.tvdb_api_key)
    try:
        result = await asyncio.to_thread(
            lambda: TVDBClient(tvdb_api_key).relations(show.title)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TheTVDB could not be reached: {exc}"
        ) from exc
    return {**result, "configured": True}


@router.get("/{show_id}/recommended")
async def get_show_recommended(
    show_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    show = await _get_show_or_404(show_id, db, current_user.id)
    app_integrations = await get_or_create_app_integration_settings(db)
    if not app_integrations.tmdb_api_key:
        return {"recommended": [], "configured": False}
    tmdb_api_key = decrypt_secret(app_integrations.tmdb_api_key)
    try:
        recommended = await asyncio.to_thread(
            lambda: TMDBClient(tmdb_api_key).tv_recommendations(show.title)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB could not be reached: {exc}"
        ) from exc
    return {"recommended": recommended, "configured": True}
