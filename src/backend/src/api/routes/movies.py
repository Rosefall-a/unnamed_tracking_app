"""API routes for managing movies."""

import re
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.movie import MovieCreate, MovieRead, MovieUpdate
from src.core.auth import get_current_user
from src.database.models.movies import Movie, MovieStatus
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/movie", tags=["movie"], dependencies=[Depends(get_current_user)])

_LEADING_ARTICLE = re.compile(r"^(a|an|the)\s+", flags=re.IGNORECASE)


def _derive_sort_title(title: str) -> str:
    """'The Matrix' -> 'matrix' so articles do not affect sort order."""
    return _LEADING_ARTICLE.sub("", title).strip().lower()


async def _get_movie_or_404(
    movie_id: UUID, db: AsyncSession, user_id: UUID, include_deleted: bool = False
) -> Movie:
    stmt = select(Movie).where(Movie.id == movie_id, Movie.user_id == user_id)
    if not include_deleted:
        stmt = stmt.where(Movie.deleted_at.is_(None))
    movie = await db.scalar(stmt)
    if movie is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Movie {movie_id} not found",
        )
    return movie


@router.post(
    "/create",
    response_model=MovieRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_movie(
    payload: MovieCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
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


@router.get("/list", response_model=list[MovieRead])
async def list_movies(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: MovieStatus | None = Query(default=None, alias="status"),
    favorite: bool | None = Query(default=None),
    search: str | None = Query(default=None, description="Case-insensitive title search"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[Movie]:
    """Return the current user's movies, filtered by status, favorite flag, or title search."""
    stmt = select(Movie).where(Movie.user_id == current_user.id, Movie.deleted_at.is_(None))

    if status_filter is not None:
        stmt = stmt.where(Movie.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(Movie.favorite == favorite)
    if search:
        stmt = stmt.where(Movie.title.ilike(f"%{search}%"))

    stmt = stmt.order_by(Movie.sort_title).offset(skip).limit(limit)

    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.get("/get/{movie_id}", response_model=MovieRead)
async def get_movie(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Movie:
    """Return one movie by ID."""
    return await _get_movie_or_404(movie_id, db, current_user.id)


@router.patch("/update/{movie_id}", response_model=MovieRead)
async def update_movie(
    movie_id: UUID,
    payload: MovieUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Movie:
    """Update a movie and keep its derived sort title synchronized."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id)

    updates = payload.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(movie, field, value)

    if "title" in updates and "sort_title" not in updates:
        movie.sort_title = _derive_sort_title(movie.title)

    await db.commit()
    await db.refresh(movie)
    return movie


@router.delete("/delete/{movie_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_movie(
    movie_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Soft-delete a movie by ID."""
    movie = await _get_movie_or_404(movie_id, db, current_user.id)
    movie.deleted_at = int(time.time())
    await db.commit()
