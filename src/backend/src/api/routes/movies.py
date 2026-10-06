"""API routes for managing movies."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.media_common import (
    LibraryFilters,
    library_page,
    owned_row,
    purge_row,
    request_metadata,
    restore_row,
    search_external_metadata,
    soft_delete,
    title_search,
    tmdb_recommendations,
    trash_listing,
)
from src.api.routes.media_extras import log_activity, status_change_detail
from src.api.schemas.metadata import MetadataSearchResponse
from src.api.schemas.movie import MovieCreate, MovieRead, MovieUpdate
from src.api.schemas.pagination import LibraryQuery, PaginatedResponse
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import get_current_user
from src.core.integrations import resolve_integrations
from src.core.titles import derive_sort_title as _derive_sort_title
from src.database.models.media_extras import ActivityEventType
from src.database.models.movies import Movie, MovieStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.locked_fields import apply_updates_with_locking
from src.features.metadata.movies.search import search_movie_metadata
from src.features.metadata.movies.tmdb import TMDBClient

_QUERY_DEFAULT = Query(..., min_length=2, max_length=100, alias="query")
_LIMIT_DEFAULT = Query(default=8, ge=1, le=20, alias="limit")
_DB_DEFAULT = Depends(get_db)
_CURRENT_USER_DEFAULT = Depends(get_current_user)


router = APIRouter(prefix="/api/movie", tags=["movie"], dependencies=[Depends(get_current_user)])

# fields the metadata search's "Apply" button can fill in — the only ones
# worth locking, since nothing else is ever set by that flow
_LOCKABLE_FIELDS = frozenset(
    {
        "title",
        "description",
        "release_date",
        "runtime_minutes",
        "director",
        "writer",
        "studios",
        "genres",
        "poster_url",
        "backdrop_url",
        "tmdb_score",
    }
)


class MovieMetadataSearchResponse(MetadataSearchResponse):
    # Keep the existing named HTTP schema; all data fields belong to its shared base.
    # pylint: disable=too-few-public-methods
    pass


async def _get_movie_or_404(
    movie_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Movie:
    return await owned_row(
        db,
        Movie,
        movie_id,
        user_id,
        "Movie",
        include_deleted=include_deleted,
        populate_existing=False,
    )


@router.get("/metadata/search", response_model=MovieMetadataSearchResponse)
async def search_metadata(
    query: str = _QUERY_DEFAULT,
    limit: int = _LIMIT_DEFAULT,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """Search TMDB and OMDb for data that can prefill a new movie. Two
    sources on purpose — redundancy, so a missing/rate-limited source
    doesn't leave the search empty."""
    del current_user
    return await search_external_metadata(db, search_movie_metadata, query, limit)


@router.post(
    "/create",
    response_model=MovieRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    payload: MovieCreate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Movie:
    """Create a movie entry."""
    data = payload.model_dump()
    if not data.get("sort_title"):
        data["sort_title"] = _derive_sort_title(data["title"])

    movie = Movie(**data, user_id=current_user.id)
    db.add(movie)
    await db.commit()
    await db.refresh(movie)
    return movie


# Typed route adapters retain their own HTTP schemas and ownership checks; behavior is shared.
# pylint: disable=duplicate-code
@router.get("/list", response_model=PaginatedResponse[MovieRead])
async def list_movies(
    query: Annotated[LibraryQuery[MovieStatus], Query()],
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> PaginatedResponse[MovieRead]:
    """Return one page of the current user's movies and the total matching it."""
    return await library_page(
        db,
        Movie,
        current_user.id,
        skip=query.skip,
        limit=query.limit,
        filters=LibraryFilters.from_query(
            query,
            MovieStatus,
            search_clause=title_search([Movie.title], query.search),
            year_column=Movie.release_date,
        ),
    )


# pylint: enable=duplicate-code


@router.get("/get/{movie_id}", response_model=MovieRead)
async def get_movie(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Movie:
    """Return one movie by ID."""
    return await _get_movie_or_404(movie_id, db, current_user.id)


# statuses that mean "not started yet" (the UI's Plan to Watch): recording
# where you left off moves a movie out of these into In progress. BACKLOG is
# the UI's On Hold, a paused watch, so it keeps its status.
_NOT_STARTED_STATUSES = {MovieStatus.WISHLIST, MovieStatus.WATCHLIST}
_FINISHED_STATUSES = {MovieStatus.WATCHED, MovieStatus.FAVORITE}


def _sync_watch_progress(movie: Movie, updates: dict) -> None:
    """Keep the left-off point and the status telling the same story (#191):
    saving a position in a movie you hadn't started means you're watching
    it, and finishing it (Watched) means there's no position to resume."""
    progress_set = bool(updates.get("progress_minutes"))
    if progress_set and "status" not in updates and movie.status in _NOT_STARTED_STATUSES:
        movie.status = MovieStatus.IN_PROGRESS
    if "status" in updates and movie.status in _FINISHED_STATUSES and not progress_set:
        movie.progress_minutes = None


@router.patch("/update/{movie_id}", response_model=MovieRead)
async def update_movie(
    movie_id: UUID,
    payload: MovieUpdate,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Movie:
    """Update a movie and keep its derived sort title synchronized."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    previous_status = movie.status

    updates = payload.model_dump(exclude_unset=True)

    apply_updates_with_locking(movie, updates, _LOCKABLE_FIELDS)
    _sync_watch_progress(movie, updates)

    if "title" in updates and "sort_title" not in updates:
        movie.sort_title = _derive_sort_title(movie.title)

    if "status" in updates and movie.status != previous_status:
        change = status_change_detail(previous_status, movie.status)
        if change:
            await log_activity(
                db,
                current_user.id,
                "movie",
                movie.id,
                movie.title,
                ActivityEventType.STATUS_CHANGED,
                date.today(),
                detail=change,
            )

    await db.commit()
    await db.refresh(movie)
    return movie


@router.delete("/delete/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Soft-delete a movie by ID."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    await soft_delete(db, movie)


@router.get("/trash")
async def list_movie_trash(
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> list[dict]:
    """Deleted movies, most recently deleted first. No purge job runs
    against these — unlike Game's on-disk folders, a movie is just a
    row, so there's nothing to clean up and it stays here until an
    admin either restores it or deletes it again to purge it for good."""
    return await trash_listing(db, Movie, current_user.id)


@router.post("/{movie_id}/restore", response_model=MovieRead)
async def restore_movie(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> Movie:
    movie = await _get_movie_or_404(movie_id, db, current_user.id, include_deleted=True)
    await restore_row(db, movie, "Movie")
    await db.refresh(movie)
    return movie


@router.delete("/{movie_id}/purge", status_code=status.HTTP_204_NO_CONTENT)
async def purge_movie(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> None:
    """Permanently removes an already-deleted movie. Only reachable from
    trash — a movie still active must be soft-deleted first."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id, include_deleted=True)
    await purge_row(db, movie, "Movie")


@router.get("/{movie_id}/relations")
async def get_movie_relations(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    """TMDB's only real franchise concept for movies: the collection a
    title belongs to (e.g. every Mad Max film). Most movies aren't in
    one — that's a normal empty result, not an error."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    if not app_integrations.tmdb_api_key:
        return {"collection_name": None, "related": [], "configured": False}
    tmdb_api_key = app_integrations.tmdb_api_key
    result = await request_metadata(
        lambda: TMDBClient(tmdb_api_key).movie_relations(movie.title), "TMDB"
    )
    return {**result, "configured": True}


@router.get("/{movie_id}/recommended")
async def get_movie_recommended(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    return await tmdb_recommendations(db, movie.title, "movie")
