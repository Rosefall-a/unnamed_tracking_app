"""API routes for managing movies."""

import asyncio
import re
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes.media_common import (
    library_page,
    purge_row,
    restore_row,
    soft_delete,
    title_search,
    trash_listing,
)
from src.api.routes.media_extras import log_activity, status_change_detail
from src.api.schemas.movie import MovieCreate, MovieRead, MovieUpdate
from src.api.schemas.pagination import PaginatedResponse
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.auth import AuthenticatedActor, get_current_actor, get_current_user
from src.core.integrations import resolve_integrations
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
_STATUS_FILTER_DEFAULT = Query(default=None, alias="status")
_FAVORITE_DEFAULT = Query(default=None, alias="favorite")
_SEARCH_DEFAULT = Query(default=None, description="Case-insensitive title search", alias="search")
_SKIP_DEFAULT = Query(default=0, ge=0, alias="skip")
_LIMIT_DEFAULT_2 = Query(default=100, ge=1, le=200, alias="limit")
_STATUS_BUCKET_DEFAULT = Query(default=None, alias="status_bucket")
_GENRE_DEFAULT = Query(default=[], alias="genre")
_GENRE_MATCH_ALL_DEFAULT = Query(default=False, alias="genre_match_all")
_FORMAT_DEFAULT = Query(default=[], alias="format")
_ONLY_UNRATED_DEFAULT = Query(default=False, alias="only_unrated")
_ONLY_WITH_NOTE_DEFAULT = Query(default=False, alias="only_with_note")
_MIN_SCORE_DEFAULT = Query(default=None, ge=0, le=10, alias="min_score")
_YEAR_FROM_DEFAULT = Query(default=None, ge=1, le=9999, alias="year_from")
_YEAR_TO_DEFAULT = Query(default=None, ge=1, le=9999, alias="year_to")

_ACTOR_DEPENDENCY = Depends(get_current_actor)

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


class MovieMetadataSearchResponse(BaseModel):
    query: str
    providers: list[str]
    provider_errors: list[str] = []
    results: list[dict]


_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


def _derive_sort_title(title: str) -> str:
    """'The Matrix' -> 'matrix' so articles do not affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


async def _get_movie_or_404(
    movie_id: UUID,
    db: AsyncSession,
    user_id: UUID,
    include_deleted: bool = False,
    *,
    for_update: bool = False,
) -> Movie:
    stmt = select(Movie).where(Movie.id == movie_id, Movie.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Movie.deleted_at.is_(None))
    if for_update:
        stmt = stmt.with_for_update().execution_options(populate_existing=True)
    movie = await db.scalar(stmt)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie {movie_id} not found",
        )
    return movie


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
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    try:
        result = await asyncio.to_thread(
            search_movie_metadata,
            query.strip(),
            limit,
            app_integrations.tmdb_api_key,
            app_integrations.omdb_api_key,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Metadata providers could not be reached: {exc}",
        ) from exc
    return result


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


@router.get("/list", response_model=PaginatedResponse[MovieRead])
async def list_movies(
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
    status_filter: MovieStatus | None = _STATUS_FILTER_DEFAULT,
    favorite: bool | None = _FAVORITE_DEFAULT,
    search: str | None = _SEARCH_DEFAULT,
    skip: int = _SKIP_DEFAULT,
    limit: int = _LIMIT_DEFAULT_2,
    status_bucket: str | None = _STATUS_BUCKET_DEFAULT,
    genre: list[str] = _GENRE_DEFAULT,
    genre_match_all: bool = _GENRE_MATCH_ALL_DEFAULT,
    format: list[str] = _FORMAT_DEFAULT,
    only_unrated: bool = _ONLY_UNRATED_DEFAULT,
    only_with_note: bool = _ONLY_WITH_NOTE_DEFAULT,
    min_score: float | None = _MIN_SCORE_DEFAULT,
    year_from: int | None = _YEAR_FROM_DEFAULT,
    year_to: int | None = _YEAR_TO_DEFAULT,
) -> PaginatedResponse[MovieRead]:
    """Return one page of the current user's movies and the total matching it."""
    status_values = None
    if status_bucket and status_bucket != "all":
        status_values = {
            "plan": {MovieStatus.WISHLIST, MovieStatus.WATCHLIST},
            "hold": {MovieStatus.BACKLOG},
            "watching": {MovieStatus.IN_PROGRESS, MovieStatus.REWATCH},
            "completed": {MovieStatus.WATCHED, MovieStatus.FAVORITE},
            "dropped": {MovieStatus.DROPPED},
        }.get(status_bucket)
        if status_values is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status bucket."
            )
    return await library_page(
        db,
        Movie,
        current_user.id,
        status_filter=status_filter,
        favorite=favorite,
        search_clause=title_search([Movie.title], search),
        skip=skip,
        limit=limit,
        status_values=status_values,
        genres=genre,
        genre_match_all=genre_match_all,
        formats=format,
        only_unrated=only_unrated,
        only_with_note=only_with_note,
        min_score=min_score,
        year_column=Movie.release_date,
        year_from=year_from,
        year_to=year_to,
    )


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
    actor: AuthenticatedActor = _ACTOR_DEPENDENCY,
) -> Movie:
    """Update a movie and keep its derived sort title synchronized."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id, for_update=True)
    previous_status = movie.status

    updates = payload.model_dump(exclude_unset=True)

    apply_updates_with_locking(movie, updates, _LOCKABLE_FIELDS, actor=actor)
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
    try:
        result = await asyncio.to_thread(
            lambda: TMDBClient(tmdb_api_key).movie_relations(movie.title)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB could not be reached: {exc}"
        ) from exc
    return {**result, "configured": True}


@router.get("/{movie_id}/recommended")
async def get_movie_recommended(
    movie_id: UUID,
    db: AsyncSession = _DB_DEFAULT,
    current_user: User = _CURRENT_USER_DEFAULT,
) -> dict:
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    app_integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    if not app_integrations.tmdb_api_key:
        return {"recommended": [], "configured": False}
    tmdb_api_key = app_integrations.tmdb_api_key
    try:
        recommended = await asyncio.to_thread(
            lambda: TMDBClient(tmdb_api_key).movie_recommendations(movie.title)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=f"TMDB could not be reached: {exc}"
        ) from exc
    return {"recommended": recommended, "configured": True}
