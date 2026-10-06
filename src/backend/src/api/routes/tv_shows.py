"""API routes for managing TV shows and their seasons."""

import asyncio
import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.media_common import (
    LibraryFilters,
    library_page,
    owned_row,
    purge_row,
    related_row,
    request_metadata,
    restore_row,
    search_external_metadata,
    soft_delete,
    title_search,
    tmdb_recommendations,
    trash_listing,
    update_tracking,
)
from src.api.routes.media_extras import log_episode_progress
from src.api.schemas.metadata import MetadataSearchResponse
from src.api.schemas.pagination import LibraryQuery, PaginatedResponse
from src.api.schemas.tv_show import (
    EpisodesBulkWatched,
    EpisodeUpdate,
    SeasonCreate,
    SeasonUpdate,
    TVShowCreate,
    TVShowLibraryRead,
    TVShowRead,
    TVShowUpdate,
)
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.titles import derive_sort_title as _derive_sort_title
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow, TVShowStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.episode_progress import (
    set_episodes_watched,
    update_episode_progress,
    update_season_progress,
)
from src.features.metadata.refresh import merge_episodes, quick_check_tv_season
from src.features.metadata.tv.episode_sync import fetch_season_episodes
from src.features.metadata.tv.search import search_tv_metadata
from src.features.metadata.tv.tvdb import TVDBClient
from src.features.tv_seasons import check_in_background, is_due

_QUERY_DEFAULT = Query(..., min_length=2, max_length=100, alias="query")
_LIMIT_DEFAULT = Query(default=8, ge=1, le=20, alias="limit")
_DB_DEFAULT = Depends(get_db)
_CURRENT_USER_DEFAULT = Depends(get_current_user)


router = APIRouter(prefix="/api/tv", tags=["tv"], dependencies=[Depends(get_current_user)])
logger = logging.getLogger(__name__)

# fields the metadata search's "Apply" button can fill in — the only ones
# worth locking, since nothing else is ever set by that flow
# Provider-owned fields differ by media kind and intentionally overlap.
# pylint: disable=duplicate-code
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

# pylint: enable=duplicate-code


class TVMetadataSearchResponse(MetadataSearchResponse):
    # Keep the existing named HTTP schema; all data fields belong to its shared base.
    # pylint: disable=too-few-public-methods
    pass


async def _get_show_or_404(
    show_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> TVShow:
    return await owned_row(
        db,
        TVShow,
        show_id,
        user_id,
        "Show",
        include_deleted=include_deleted,
        populate_existing=True,
    )


async def _get_season_or_404(season_id: UUID, show_id: UUID, db: AsyncSession) -> TVSeason:
    return await related_row(
        db, TVSeason, season_id, parent_column=TVSeason.show_id, parent_id=show_id, label="Season"
    )


@router.get("/metadata/search", response_model=TVMetadataSearchResponse)
async def search_metadata(
    query: str = _QUERY_DEFAULT,
    limit: int = _LIMIT_DEFAULT,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """Search TMDB and OMDb for data that can prefill a new show,
    including its full season list where TMDB has it."""
    del current_user
    return await search_external_metadata(db, search_tv_metadata, query, limit)


@router.post("/create", response_model=TVShowRead, status_code=status.HTTP_201_CREATED)
async def create_show(
    payload: TVShowCreate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
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

    first_season = None
    for season_input in payload.seasons:
        season = TVSeason(**season_input.model_dump(), show_id=show.id)
        db.add(season)
        if first_season is None:
            first_season = season

    # Otherwise a freshly-added airing show shows no next-episode date
    # anywhere (countdown, calendar) until the next periodic airing-check
    # pass, up to one airing-check interval later — worth the one
    # extra TVmaze call at creation time so it's there immediately.
    # Best-effort: a slow/unreachable TVmaze never blocks creation.
    if show.external_id and first_season is not None:
        try:
            await quick_check_tv_season(show, first_season, db)
        # Optional provider enrichment must not abort creation of the user's title.
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("Immediate airing check failed for new show %r", show.title)

    await db.commit()
    return await _get_show_or_404(show.id, db, current_user.id)


@router.post("/{show_id}/refresh-airing", response_model=TVShowRead)
async def refresh_airing(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    """Runs the airing check for just this show right now (the background
    loop only comes around every 30 minutes)."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    if not show.external_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This show has no TVmaze id, so its airing schedule can't be checked.",
        )
    if show.seasons:
        await quick_check_tv_season(show, show.seasons[-1], db)
        await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.get("/list", response_model=PaginatedResponse[TVShowLibraryRead])
async def list_shows(
    query: Annotated[LibraryQuery[TVShowStatus], Query()],
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> PaginatedResponse[TVShowLibraryRead]:
    """Return one page of the current user's shows and the total matching it."""
    return await library_page(
        db,
        TVShow,
        current_user.id,
        skip=query.skip,
        limit=query.limit,
        filters=LibraryFilters.from_query(
            query,
            TVShowStatus,
            search_clause=title_search([TVShow.title], query.search),
            year_column=TVShow.first_air_date,
        ),
    )


# pylint: enable=duplicate-code


@router.get("/get/{show_id}", response_model=TVShowRead)
async def get_show(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    """Return one show by ID, with its seasons. If it has been a while,
    also asks TVmaze in the background whether the show has a new season
    (see features/tv_seasons.py), which shows up the next time it's opened."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    if is_due(show):
        asyncio.create_task(check_in_background(show.id))
    return show


@router.patch("/update/{show_id}", response_model=TVShowRead)
async def update_show(
    show_id: UUID,
    payload: TVShowUpdate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    """Update a show and keep its derived sort title synchronized."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    await update_tracking(db, show, payload.model_dump(exclude_unset=True), _LOCKABLE_FIELDS, "tv")

    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/delete/{show_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_show(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Soft-delete a show by ID (its seasons stay attached, hidden along with it)."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    await soft_delete(db, show)


@router.get("/trash")
async def list_show_trash(
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> list[dict]:
    """Deleted shows, most recently deleted first. No purge job runs
    against these — unlike Game's on-disk folders, a show is just a row
    (plus its seasons/episodes), so there's nothing to clean up and it
    stays here until an admin either restores it or purges it for good."""
    return await trash_listing(db, TVShow, current_user.id)


@router.post("/{show_id}/restore", response_model=TVShowRead)
async def restore_show(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    show = await _get_show_or_404(show_id, db, current_user.id, include_deleted=True)
    await restore_row(db, show, "Show")
    return await _get_show_or_404(show_id, db, current_user.id)


@router.delete("/{show_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_show(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Permanently removes an already-deleted show and its seasons/
    episodes. Only reachable from trash — a show still active must be
    soft-deleted first."""
    show = await _get_show_or_404(show_id, db, current_user.id, include_deleted=True)
    await purge_row(db, show, "Show")


@router.post("/{show_id}/seasons", response_model=TVShowRead, status_code=status.HTTP_201_CREATED)
async def create_season(
    show_id: UUID,
    payload: SeasonCreate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    show = await _get_show_or_404(show_id, db, current_user.id)
    db.add(TVSeason(**payload.model_dump(), show_id=show.id))
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.patch("/{show_id}/seasons/{season_id}", response_model=TVShowRead)
async def update_season(
    show_id: UUID,
    season_id: UUID,
    payload: SeasonUpdate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    newly_watched = update_season_progress(season, payload.model_dump(exclude_unset=True))
    await log_episode_progress(db, current_user.id, show, "tv", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# pylint: enable=duplicate-code


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.delete("/{show_id}/seasons/{season_id}", response_model=TVShowRead)
async def delete_season(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    await db.delete(season)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# pylint: enable=duplicate-code


async def _get_episode_or_404(episode_id: UUID, season_id: UUID, db: AsyncSession) -> TVEpisode:
    return await related_row(
        db,
        TVEpisode,
        episode_id,
        parent_column=TVEpisode.season_id,
        parent_id=season_id,
        label="Episode",
    )


@router.get("/{show_id}/seasons/{season_id}/episodes", response_model=TVShowRead)
async def list_episodes(
    show_id: UUID,
    season_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    """Return the season's episodes, syncing them in from TVmaze on the
    very first request (nothing to sync from if the show has no
    `external_id` — it wasn't found via TVmaze, e.g. added by hand).
    Every later call reads straight from the table instead of
    re-fetching."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)

    if not season.episodes and show.external_id:
        all_episodes, errors = await fetch_season_episodes(show.external_id, season.season_number)
        if not all_episodes and errors:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Could not sync episodes: {'; '.join(errors)}",
            )
        # Initial listings preserve their existing date-only payload; timed refreshes also save air_at.
        merge_episodes(db, season, all_episodes, TVEpisode, include_air_at=False)
        await db.commit()

    return await _get_show_or_404(show_id, db, current_user.id)


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.patch("/{show_id}/seasons/{season_id}/episodes/bulk-watched", response_model=TVShowRead)
async def bulk_set_episodes_watched(
    show_id: UUID,
    season_id: UUID,
    payload: EpisodesBulkWatched,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    """Sets `watched` on a whole batch of episodes in one request — see
    the anime version of this route for why. Registered ahead of the
    single-episode PATCH below so the literal path segment
    "bulk-watched" is matched here rather than attempted as an
    `episode_id` UUID."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    newly_watched = set_episodes_watched(season, set(payload.episode_ids), payload.watched)
    await log_episode_progress(db, current_user.id, show, "tv", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# pylint: enable=duplicate-code


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.patch("/{show_id}/seasons/{season_id}/episodes/{episode_id}", response_model=TVShowRead)
async def update_episode(
    show_id: UUID,
    season_id: UUID,
    episode_id: UUID,
    payload: EpisodeUpdate,
    *,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> TVShow:
    show = await _get_show_or_404(show_id, db, current_user.id)
    season = await _get_season_or_404(season_id, show_id, db)
    episode = await _get_episode_or_404(episode_id, season_id, db)

    newly_watched = update_episode_progress(season, episode, payload.model_dump(exclude_unset=True))

    await log_episode_progress(db, current_user.id, show, "tv", newly_watched)
    await db.commit()
    return await _get_show_or_404(show_id, db, current_user.id)


# pylint: enable=duplicate-code


@router.get("/{show_id}/relations")
async def get_show_relations(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """TheTVDB is the only real franchise/relations source for TV shows —
    TMDB has no collection concept outside of movies. Requires its own
    API key (Settings > Metadata Sources); returns an empty, clearly
    unconfigured result rather than an error when it's not set up yet."""
    show = await _get_show_or_404(show_id, db, current_user.id)
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    if not app_integrations.tvdb_api_key:
        return {"listName": None, "related": [], "configured": False}
    tvdb_api_key = app_integrations.tvdb_api_key
    result = await request_metadata(
        lambda: TVDBClient(tvdb_api_key).relations(show.title), "TheTVDB"
    )
    return {**result, "configured": True}


@router.get("/{show_id}/recommended")
async def get_show_recommended(
    show_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    show = await _get_show_or_404(show_id, db, current_user.id)
    return await tmdb_recommendations(db, show.title, "tv")
