"""Shared response models for paginated library endpoints."""

# Pylint associates the upload-route similarity with this shared schema module;
# the routes intentionally retain separate media/game validation paths.
# pylint: disable=duplicate-code

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


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
    from sqlalchemy import select

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
