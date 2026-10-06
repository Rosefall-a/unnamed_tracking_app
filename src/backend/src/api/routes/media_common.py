"""What the movie, TV show and anime routes do the same way: the library list
with its status counts and ranks, and the soft-delete / trash / restore /
purge life cycle. Each route module passes in its own model and wording."""

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import Enum
from typing import Any, Literal, ParamSpec, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import count as sql_count

from src.api.routes.media_extras import log_status_change
from src.api.schemas.pagination import LibraryQuery, PaginatedResponse, score_ranks
from src.core.app_integrations import get_or_create_app_integration_settings
from src.core.integrations import resolve_integrations
from src.core.titles import derive_sort_title
from src.features.metadata.locked_fields import apply_updates_with_locking
from src.features.metadata.movies.tmdb import TMDBClient

P = ParamSpec("P")
ResultT = TypeVar("ResultT")


async def request_metadata(
    provider: Callable[P, ResultT], error_label: str, *args: P.args, **kwargs: P.kwargs
) -> ResultT:
    """Call blocking providers off the event loop and preserve the API's 502 response."""
    try:
        return await asyncio.to_thread(provider, *args, **kwargs)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY, f"{error_label} could not be reached: {exc}"
        ) from exc


async def owned_row(
    db: AsyncSession,
    model: Any,
    row_id: Any,
    user_id: Any,
    label: str,
    *,
    include_deleted: bool = False,
    populate_existing: bool = False,
) -> Any:
    """Resolve an owned media row; only trash operations include deleted rows."""
    stmt = select(model).where(model.id == row_id, model.user_id == user_id)
    if populate_existing:
        stmt = stmt.execution_options(populate_existing=True)
    if not include_deleted:
        stmt = stmt.where(model.deleted_at.is_(None))
    row = await db.scalar(stmt)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} {row_id} not found")
    return row


async def related_row(
    db: AsyncSession, model: Any, row_id: Any, *, parent_column: Any, parent_id: Any, label: str
) -> Any:
    """Resolve a child only within the parent already authorized by the route."""
    row = await db.scalar(select(model).where(model.id == row_id, parent_column == parent_id))
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"{label} {row_id} not found")
    return row


async def search_external_metadata(
    db: AsyncSession, provider: Callable[..., dict], query: str, limit: int
) -> dict:
    """Use the app's TMDB and OMDb credentials for either native film or TV search."""
    integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    return await request_metadata(
        provider,
        "Metadata providers",
        query.strip(),
        limit,
        integrations.tmdb_api_key,
        integrations.omdb_api_key,
    )


async def tmdb_recommendations(
    db: AsyncSession, title: str, media_type: Literal["movie", "tv"]
) -> dict:
    integrations = resolve_integrations(await get_or_create_app_integration_settings(db))
    if not integrations.tmdb_api_key:
        return {"recommended": [], "configured": False}
    client = TMDBClient(integrations.tmdb_api_key)
    provider = client.movie_recommendations if media_type == "movie" else client.tv_recommendations
    recommended = await request_metadata(provider, "TMDB", title)
    return {"recommended": recommended, "configured": True}


async def update_tracking(
    db: AsyncSession,
    row: Any,
    updates: dict[str, Any],
    lockable_fields: frozenset[str],
    media_type: str,
) -> None:
    """Apply media edits, keep title ordering, and record a meaningful status transition."""
    previous_status = row.status
    apply_updates_with_locking(row, updates, lockable_fields)
    if "title" in updates and "sort_title" not in updates:
        row.sort_title = derive_sort_title(row.title)
    if "status" in updates:
        await log_status_change(db, row.user_id, row, media_type, previous_status)


def title_search(columns: list[Any], search: str | None) -> ColumnElement[bool] | None:
    """A case-insensitive "contains" match of `search` against any of the title
    columns. `%` and `_` typed by the user match themselves, not anything."""
    text = (search or "").strip()
    if not text:
        return None
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return or_(*(column.ilike(f"%{escaped}%", escape="\\") for column in columns))


@dataclass(frozen=True, kw_only=True)
class LibraryFilters:
    """The same selected filters feed library rows and every status tab."""

    # This value object represents the existing independent library filters.
    # pylint: disable=too-many-instance-attributes
    status_filter: Any = None
    favorite: bool | None = None
    search_clause: ColumnElement[bool] | None = None
    status_values: set[Any] | None = None
    genres: list[str] | None = None
    genre_match_all: bool = False
    formats: list[str] | None = None
    only_unrated: bool = False
    only_with_note: bool = False
    min_score: float | None = None
    year_column: Any | None = None
    year_from: int | None = None
    year_to: int | None = None

    @classmethod
    def from_query(
        cls,
        query: LibraryQuery[Any],
        status_type: type[Enum],
        *,
        search_clause: ColumnElement[bool] | None,
        year_column: Any,
    ) -> "LibraryFilters":
        return cls(
            status_filter=query.status,
            favorite=query.favorite,
            search_clause=search_clause,
            status_values=_status_bucket(status_type, query.status_bucket),
            genres=query.genre,
            genre_match_all=query.genre_match_all,
            formats=query.format,
            only_unrated=query.only_unrated,
            only_with_note=query.only_with_note,
            min_score=query.min_score,
            year_column=year_column,
            year_from=query.year_from,
            year_to=query.year_to,
        )


# Parallel routes/models intentionally share this shape.
# pylint: disable=duplicate-code
def _status_bucket(status_type: type[Enum], bucket: str | None) -> set[Enum] | None:
    if not bucket or bucket == "all":
        return None
    values = {
        "plan": {"WISHLIST", "WATCHLIST"},
        "hold": {"BACKLOG"},
        "watching": {"IN_PROGRESS", "REWATCH"},
        "completed": {"WATCHED", "FAVORITE"},
        "dropped": {"DROPPED"},
    }.get(bucket)
    if values is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid status bucket.")
    return {status_type(value) for value in values}


# pylint: enable=duplicate-code


def _library_statement(model: Any, user_id: Any, filters: LibraryFilters) -> Select[Any]:
    """Apply the shared filters, leaving the active status tab to the caller."""
    stmt = select(model).where(model.user_id == user_id, model.deleted_at.is_(None))
    if filters.favorite is not None:
        stmt = stmt.where(model.favorite == filters.favorite)
    if filters.search_clause is not None:
        stmt = stmt.where(filters.search_clause)
    if filters.status_values:
        stmt = stmt.where(model.status.in_(filters.status_values))
    if filters.genres:
        genre_clauses = [model.genres.contains([genre]) for genre in filters.genres]
        stmt = stmt.where(*(genre_clauses if filters.genre_match_all else [or_(*genre_clauses)]))
    format_column = getattr(model, "format", None)
    if filters.formats and format_column is not None:
        stmt = stmt.where(format_column.in_(filters.formats))
    if filters.only_unrated:
        stmt = stmt.where(model.rating_overall.is_(None))
    if filters.only_with_note:
        stmt = stmt.where(model.note.is_not(None), func.trim(model.note) != "")
    if filters.min_score is not None:
        stmt = stmt.where(model.rating_overall >= filters.min_score)
    if filters.year_column is not None:
        if filters.year_from is not None:
            stmt = stmt.where(filters.year_column >= date(filters.year_from, 1, 1))
        if filters.year_to is not None:
            stmt = stmt.where(filters.year_column <= date(filters.year_to, 12, 31))

    return stmt


async def library_page(
    db: AsyncSession,
    model: Any,
    user_id: Any,
    *,
    filters: LibraryFilters,
    skip: int,
    limit: int,
) -> PaginatedResponse[Any]:
    """Filter before pagination, while status tabs count every matching status.

    Rankings cover the user's complete rated library, independently of the filters.
    """
    stmt = _library_statement(model, user_id, filters)
    count_stmt = stmt.with_only_columns(model.status, sql_count()).group_by(model.status)
    counts_result = await db.execute(count_stmt)
    status_counts = {row_status.value: count for row_status, count in counts_result.all()}
    if filters.status_filter is not None:
        stmt = stmt.where(model.status == filters.status_filter)
    total = await db.scalar(select(sql_count()).select_from(stmt.subquery()))
    stmt = stmt.order_by(model.sort_title).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return PaginatedResponse(
        items=list(result.scalars().unique().all()),
        total=total or 0,
        offset=skip,
        limit=limit,
        status_counts=status_counts,
        score_ranks=await score_ranks(db, model, user_id),
    )


async def soft_delete(db: AsyncSession, row: Any) -> None:
    """Hide a row without removing it, so it can be restored from the trash."""
    row.deleted_at = int(time.time())
    await db.commit()


async def trash_listing(db: AsyncSession, model: Any, user_id: Any) -> list[dict]:
    """A user's deleted rows, most recently deleted first. Nothing purges
    these on a schedule: a row is only data, so there is nothing to clean up
    and it stays until it is restored or purged."""
    result = await db.execute(
        select(model)
        .where(model.user_id == user_id, model.deleted_at.is_not(None))
        .order_by(model.deleted_at.desc())
    )
    return [
        {"id": str(row.id), "title": row.title, "deleted_at": row.deleted_at}
        for row in result.scalars().all()
    ]


def require_deleted(row: Any, label: str) -> None:
    """Restoring and purging only make sense for something in the trash."""
    if row.deleted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} isn't deleted."
        )


async def restore_row(db: AsyncSession, row: Any, label: str) -> None:
    """Take a row out of the trash."""
    require_deleted(row, label)
    row.deleted_at = None
    await db.commit()


async def purge_row(db: AsyncSession, row: Any, label: str) -> None:
    """Permanently remove a row that is already in the trash."""
    require_deleted(row, label)
    await db.delete(row)
    await db.commit()
