"""What the movie, TV show and anime routes do the same way: the library list
with its status counts and ranks, and the soft-delete / trash / restore /
purge life cycle. Each route module passes in its own model and wording."""

import time
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.pagination import PaginatedResponse, score_ranks


def title_search(columns: list[Any], search: str | None) -> ColumnElement[bool] | None:
    """A case-insensitive "contains" match of `search` against any of the title
    columns. `%` and `_` typed by the user match themselves, not anything."""
    text = (search or "").strip()
    if not text:
        return None
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return or_(*(column.ilike(f"%{escaped}%", escape="\\") for column in columns))


async def library_page(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    db: AsyncSession,
    model: Any,
    user_id: Any,
    *,
    status_filter: Any,
    favorite: bool | None,
    search_clause: ColumnElement[bool] | None,
    skip: int,
    limit: int,
    status_values: set[Any] | None = None,
    genres: list[str] | None = None,
    genre_match_all: bool = False,
    formats: list[str] | None = None,
    only_unrated: bool = False,
    only_with_note: bool = False,
    min_score: float | None = None,
    year_column: Any | None = None,
    year_from: int | None = None,
    year_to: int | None = None,
) -> PaginatedResponse[Any]:
    """One page of a user's library, the total matching it, how many titles
    sit in each status, and every rated title's rank. The status counts
    follow the favorite flag and the search but not the status filter, so the
    tabs always show what each one would hold."""
    stmt = select(model).where(model.user_id == user_id, model.deleted_at.is_(None))
    if status_filter is not None:
        stmt = stmt.where(model.status == status_filter)
    if favorite is not None:
        stmt = stmt.where(model.favorite == favorite)
    if search_clause is not None:
        stmt = stmt.where(search_clause)
    if status_values:
        stmt = stmt.where(model.status.in_(status_values))
    if genres:
        genre_clauses = [model.genres.contains([genre]) for genre in genres]
        stmt = stmt.where(*(genre_clauses if genre_match_all else [or_(*genre_clauses)]))
    format_column = getattr(model, "format", None)
    if formats and format_column is not None:
        stmt = stmt.where(format_column.in_(formats))
    if only_unrated:
        stmt = stmt.where(model.rating_overall.is_(None))
    if only_with_note:
        stmt = stmt.where(model.note.is_not(None), func.trim(model.note) != "")
    if min_score is not None:
        stmt = stmt.where(model.rating_overall >= min_score)
    if year_column is not None:
        if year_from is not None: stmt = stmt.where(year_column >= date(year_from, 1, 1))
        if year_to is not None: stmt = stmt.where(year_column <= date(year_to, 12, 31))

    count_stmt = select(model.status, func.count()).where(
        model.user_id == user_id, model.deleted_at.is_(None)
    )
    if favorite is not None:
        count_stmt = count_stmt.where(model.favorite == favorite)
    if search_clause is not None:
        count_stmt = count_stmt.where(search_clause)
    if status_values:
        count_stmt = count_stmt.where(model.status.in_(status_values))
    if genres:
        genre_clauses = [model.genres.contains([genre]) for genre in genres]
        count_stmt = count_stmt.where(*(genre_clauses if genre_match_all else [or_(*genre_clauses)]))
    format_column = getattr(model, "format", None)
    if formats and format_column is not None:
        count_stmt = count_stmt.where(format_column.in_(formats))
    if only_unrated:
        count_stmt = count_stmt.where(model.rating_overall.is_(None))
    if only_with_note:
        count_stmt = count_stmt.where(model.note.is_not(None), func.trim(model.note) != "")
    if min_score is not None:
        count_stmt = count_stmt.where(model.rating_overall >= min_score)
    if year_column is not None:
        if year_from is not None: count_stmt = count_stmt.where(year_column >= date(year_from, 1, 1))
        if year_to is not None: count_stmt = count_stmt.where(year_column <= date(year_to, 12, 31))
    counts_result = await db.execute(count_stmt.group_by(model.status))
    status_counts = {row_status.value: count for row_status, count in counts_result.all()}

    total = await db.scalar(select(func.count()).select_from(stmt.subquery()))
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
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} isn't deleted.")


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
