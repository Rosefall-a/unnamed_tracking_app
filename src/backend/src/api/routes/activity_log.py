"""Logging something that happened, from the calendar's Log button. Unlike a plain
history entry this also does it: finishing a show marks its episodes and status,
finishing a game sets its status and date."""

from __future__ import annotations

from datetime import UTC, date, datetime, time
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes import anime as anime_routes
from src.api.routes import tv_shows as tv_routes
from src.api.routes.media_extras import _resolve_media, log_activity
from src.api.schemas.media_extras import ActivityEntryRead
from src.core.auth import get_current_user
from src.database.models.anime import AnimeStatus
from src.database.models.game import Game, GameStatus
from src.database.models.media_extras import ActivityEventType, ActivityLog
from src.database.models.movies import Movie, MovieStatus
from src.database.models.tv_show import TVShowStatus
from src.database.models.user import User
from src.database.session import get_db
from src.features.episode_progress import finish_seasons
from src.helpers.game_info_file import write_game_info

router = APIRouter(
    prefix="/api/activity", tags=["activity"], dependencies=[Depends(get_current_user)]
)

Action = Literal["episodes", "finished", "played", "mastered", "bought"]
_ALLOWED: dict[str, set[str]] = {
    "movie": {"finished"},
    "tv": {"episodes", "finished"},
    "anime": {"episodes", "finished"},
    "game": {"played", "finished", "mastered", "bought"},
}
# a game that has been played has moved on from these
_NOT_STARTED = {GameStatus.BACKLOG, GameStatus.WISHLIST}


class LogAction(BaseModel):
    media_type: Literal["movie", "tv", "anime", "game"]
    media_id: UUID
    action: Action
    event_date: date
    count: int = Field(default=1, ge=1, le=100_000)
    detail: str | None = Field(default=None, max_length=200)


def _noon(day: date) -> int:
    """A chosen day with no time: noon UTC keeps it on that day in every zone."""
    return int(datetime.combine(day, time(12), tzinfo=UTC).timestamp())


async def _finish_series(db: AsyncSession, show, media_type: str) -> tuple[int, int]:
    """Marks every episode watched. Returns how many were newly marked, and how many
    seasons could not be finished because nobody knows their episode count."""
    module = tv_routes if media_type == "tv" else anime_routes
    seasons = [await module._get_season_or_404(s.id, show.id, db) for s in list(show.seasons)]
    status = TVShowStatus if media_type == "tv" else AnimeStatus
    return finish_seasons(seasons, status.WATCHED, keep=(status.WATCHED, status.FAVORITE))


@router.post("/log", response_model=ActivityEntryRead, status_code=status.HTTP_201_CREATED)
async def log_action(
    payload: LogAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ActivityLog:
    if payload.action not in _ALLOWED[payload.media_type]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{payload.action} does not apply to a {payload.media_type}.",
        )
    if payload.event_date > date.today():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="That date has not happened yet.",
        )
    media = await _resolve_media(payload.media_type, payload.media_id, current_user.id, db)
    day = payload.event_date
    event = ActivityEventType.FINISHED
    detail = payload.detail
    increment = 1

    if isinstance(media, Game):
        if payload.action == "played":
            event = ActivityEventType.PLAYED
            if media.last_played_at is None or media.last_played_at < _noon(day):
                media.last_played_at = _noon(day)
            if media.status in _NOT_STARTED:
                media.status = GameStatus.PLAYED
        elif payload.action == "bought":
            event = ActivityEventType.BOUGHT
            media.purchase_date = _noon(day)
            if media.status == GameStatus.WISHLIST:
                media.status = GameStatus.BACKLOG
        else:
            mastered = payload.action == "mastered"
            if mastered or media.status != GameStatus.MASTERED:
                media.status = GameStatus.MASTERED if mastered else GameStatus.BEATEN
            media.completion_date = _noon(day)
            detail = detail or ("Mastered" if mastered else "Beaten")
    elif isinstance(media, Movie):
        if media.status != MovieStatus.FAVORITE:
            media.status = MovieStatus.WATCHED
        media.progress_minutes = None
    elif payload.action == "episodes":
        event = ActivityEventType.EPISODES_WATCHED
        increment = payload.count
    else:
        marked, unknown = await _finish_series(db, media, payload.media_type)
        watched_status = TVShowStatus if payload.media_type == "tv" else AnimeStatus
        if media.status != watched_status.FAVORITE:
            media.status = watched_status.WATCHED
        if marked:
            await log_activity(
                db,
                current_user.id,
                payload.media_type,
                media.id,
                media.title,
                ActivityEventType.EPISODES_WATCHED,
                day,
                increment=marked,
            )
        if unknown and not detail:
            detail = f"{unknown} season{'' if unknown == 1 else 's'} with no episode count"

    await log_activity(
        db,
        current_user.id,
        payload.media_type,
        media.id,
        media.title,
        event,
        day,
        increment=increment,
        detail=detail,
    )
    await db.commit()
    if isinstance(media, Game):
        write_game_info(media)
    row = await db.scalar(
        select(ActivityLog).where(
            ActivityLog.user_id == current_user.id,
            ActivityLog.media_type == payload.media_type,
            ActivityLog.media_id == media.id,
            ActivityLog.event_type == event,
            ActivityLog.event_date == day,
        )
    )
    assert row is not None  # just written above
    return row
