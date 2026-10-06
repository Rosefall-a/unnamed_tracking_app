"""Shared response models for paginated library endpoints."""

from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field
from sqlalchemy import select

T = TypeVar("T")
StatusT = TypeVar("StatusT", bound=Enum)


class LibraryQuery(BaseModel, Generic[StatusT]):
    """Shared HTTP filters, with each media kind retaining its status enum."""

    # Independent query fields are the existing public library-filter contract.
    # pylint: disable=too-many-instance-attributes
    status: StatusT | None = None
    favorite: bool | None = None
    search: str | None = Field(default=None, description="Case-insensitive title search")
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=200)
    status_bucket: str | None = None
    genre: list[str] = []
    genre_match_all: bool = False
    format: list[str] = []
    only_unrated: bool = False
    only_with_note: bool = False
    min_score: float | None = Field(default=None, ge=0, le=10)
    year_from: int | None = Field(default=None, ge=1, le=9999)
    year_to: int | None = Field(default=None, ge=1, le=9999)


class PaginatedResponse(BaseModel, Generic[T]):
    """A page of results plus the authoritative total matching the query."""

    items: list[T]
    total: int = Field(ge=0)
    offset: int = Field(ge=0)
    limit: int = Field(gt=0)
    status_counts: dict[str, int] = Field(default_factory=dict)
    # id -> leaderboard position among everything the user has rated, highest
    # first. Covers the whole library, not just this page or search, so a
    # title's rank never depends on what happens to be loaded.
    score_ranks: dict[str, int] = Field(default_factory=dict)


async def score_ranks(db, model, user_id) -> dict[str, int]:  # type: ignore[no-untyped-def]
    """Rank every rated, non-deleted row of ``model`` for the user."""
    result = await db.execute(
        select(model.id)
        .where(
            model.user_id == user_id,
            model.deleted_at.is_(None),
            model.rating_overall.is_not(None),
        )
        .order_by(model.rating_overall.desc(), model.sort_title)
    )
    return {str(row[0]): i + 1 for i, row in enumerate(result.all())}
