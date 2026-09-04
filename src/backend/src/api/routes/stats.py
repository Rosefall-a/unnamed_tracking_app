"""API routes for the Server Stats dashboard — everything computed live
from the caller's own library, no caching/background jobs."""

import asyncio
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import get_db

router = APIRouter(prefix="/api/stats", tags=["stats"], dependencies=[Depends(get_current_user)])

_DATA_ROOT = Path("/data/games")


def _folder_size_bytes(folder_location: str | None) -> int:
    if not folder_location:
        return 0
    game_dir = _DATA_ROOT / folder_location
    if not game_dir.is_dir():
        return 0
    total = 0
    for path in game_dir.rglob("*"):
        if path.is_file():
            try:
                total += path.stat().st_size
            except OSError:
                continue
    return total


@router.get("/overview")
async def get_stats_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    user_filter = Game.user_id == current_user.id

    totals_stmt = select(
        func.count(Game.id),
        func.count(Game.id).filter(Game.favorite.is_(True)),
        func.coalesce(func.sum(Game.playtime_seconds), 0),
        func.coalesce(func.sum(Game.purchase_price), 0),
        func.avg(Game.rating_overall),
    ).where(user_filter)

    status_stmt = select(Game.status, func.count(Game.id)).where(user_filter).group_by(Game.status)
    source_stmt = select(Game.source, func.count(Game.id)).where(user_filter).group_by(Game.source)
    most_played_stmt = (
        select(Game.id, Game.title, Game.playtime_seconds)
        .where(user_filter, Game.playtime_seconds > 0)
        .order_by(Game.playtime_seconds.desc())
        .limit(10)
    )
    recent_stmt = (
        select(
            func.date_trunc("month", func.to_timestamp(Game.created_at)).label("month"),
            func.count(Game.id),
        )
        .where(user_filter)
        .group_by("month")
        .order_by("month")
    )
    folders_stmt = select(Game.folder_location).where(user_filter)

    # rating histogram — bucketed into 1-point bins, 0-10
    rating_bucket = func.floor(Game.rating_overall).label("bucket")
    rating_histogram_stmt = (
        select(rating_bucket, func.count(Game.id))
        .where(user_filter, Game.rating_overall.is_not(None))
        .group_by(rating_bucket)
        .order_by(rating_bucket)
    )

    # top tags — one row per (game, tag) via unnest, then count
    tag_column = func.unnest(Game.tags).label("tag")
    top_tags_stmt = (
        select(tag_column, func.count().label("tag_count"))
        .where(user_filter)
        .group_by(tag_column)
        .order_by(func.count().desc())
        .limit(10)
    )

    release_year_stmt = (
        select(extract("year", Game.release_date).label("year"), func.count(Game.id))
        .where(user_filter, Game.release_date.is_not(None))
        .group_by("year")
        .order_by("year")
    )

    format_case = case((Game.physical_condition.is_not(None), "Physical"), else_="Digital")
    format_stmt = select(format_case, func.count(Game.id)).where(user_filter).group_by(format_case)

    # NOTE: a single AsyncSession can't run concurrent statements — these
    # run sequentially, not via asyncio.gather, despite all being cheap
    # aggregate queries that would otherwise be a good gather() candidate.
    totals_result = await db.execute(totals_stmt)
    status_result = await db.execute(status_stmt)
    source_result = await db.execute(source_stmt)
    most_played_result = await db.execute(most_played_stmt)
    recent_result = await db.execute(recent_stmt)
    folders_result = await db.execute(folders_stmt)
    rating_histogram_result = await db.execute(rating_histogram_stmt)
    top_tags_result = await db.execute(top_tags_stmt)
    release_year_result = await db.execute(release_year_stmt)
    format_result = await db.execute(format_stmt)

    total_games, favorite_count, total_playtime_seconds, total_spent, average_rating = totals_result.one()

    folder_locations = [row[0] for row in folders_result.all()]
    storage_used_bytes = await asyncio.gather(
        *(asyncio.to_thread(_folder_size_bytes, folder) for folder in folder_locations)
    )

    return {
        "total_games": total_games,
        "favorite_count": favorite_count,
        "total_playtime_seconds": int(total_playtime_seconds),
        "storage_used_bytes": sum(storage_used_bytes),
        "total_spent": float(total_spent),
        "average_rating": float(average_rating) if average_rating is not None else None,
        "status_breakdown": [
            {"label": status.value if hasattr(status, "value") else status, "count": count}
            for status, count in status_result.all()
        ],
        "source_breakdown": [
            {"label": source or "Unknown", "count": count} for source, count in source_result.all()
        ],
        "most_played": [
            {"id": str(game_id), "title": title, "playtime_seconds": seconds}
            for game_id, title, seconds in most_played_result.all()
        ],
        "recently_added": [
            {"month": month.strftime("%Y-%m"), "count": count} for month, count in recent_result.all()
        ],
        "rating_histogram": [
            {"label": f"{int(bucket)}-{int(bucket) + 1}", "count": count}
            for bucket, count in rating_histogram_result.all()
        ],
        "top_tags": [{"label": tag, "count": count} for tag, count in top_tags_result.all() if tag],
        "release_year_breakdown": [
            {"label": str(int(year)), "count": count} for year, count in release_year_result.all()
        ],
        "format_breakdown": [{"label": label, "count": count} for label, count in format_result.all()],
    }
