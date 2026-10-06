"""Builds notifications from real, exact data. Nothing here estimates: an
episode notification exists only because a provider gave that episode an
air time (or the show's confirmed next-episode time) that has now passed,
and its `event_at` is that exact time.

There is no scheduler: generation runs when the app asks for
notifications (the bell polls), so it costs nothing while nobody is
looking and needs no new background job. Deduplication by `dedupe_key`
makes running it any number of times safe."""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.preferences import load_preferences
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason, AnimeStatus
from src.database.models.movies import Movie, MovieStatus
from src.database.models.notification import Notification
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow, TVShowStatus
from src.features.notification_providers.delivery import ensure_deliveries

# How far back "just aired" reaches. A week covers someone away for a few
# days without turning first use into a flood of old episodes.
WINDOW_SECONDS = 7 * 24 * 60 * 60


def tracked_statuses(enum_cls: Any, buckets: list[str]) -> list[Any]:
    """The statuses behind the library buckets the user switched on: watching,
    plan to watch and on hold. Used for who gets alerts and which airing shows
    reach the calendar. Completed and Dropped titles are done with and never
    appear in either."""
    by_bucket = {
        "watching": [enum_cls.IN_PROGRESS, enum_cls.REWATCH],
        "plan": [enum_cls.WISHLIST, enum_cls.WATCHLIST],
        "hold": [enum_cls.BACKLOG],
    }
    return [status for bucket in buckets for status in by_bucket.get(bucket, [])]


def _noon_utc(d: date) -> int:
    return int(datetime(d.year, d.month, d.day, 12, tzinfo=timezone.utc).timestamp())


async def _insert(db: AsyncSession, user_id: UUID, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    now = int(time.time())
    stmt = (
        pg_insert(Notification)
        .values([{**r, "user_id": user_id, "created_at": now} for r in rows])
        .on_conflict_do_nothing(constraint="uq_notifications_user_dedupe")
    )
    result = await db.execute(stmt.returning(Notification.id))
    notification_ids = list(result.scalars())
    await ensure_deliveries(db, notification_ids)
    return len(notification_ids)


def _episode_row(
    media_type: str,
    show: Anime | TVShow,
    season_number: int | None,
    episode_number: int,
    air_at: int,
    *,
    prefs: dict[str, Any],
) -> dict[str, Any] | None:
    started = episode_number == 1
    if started and not prefs["notify_season_started"]:
        return None
    if not started and not prefs["notify_episode_aired"]:
        return None
    later_season = media_type == "tv" and season_number is not None and season_number > 1
    if started:
        kind = "season_started"
        body = (
            f"Season {season_number} has started airing" if later_season else "Has started airing"
        )
    else:
        kind = "episode_aired"
        body = (
            f"Season {season_number} episode {episode_number} aired"
            if later_season
            else f"Episode {episode_number} aired"
        )
    return {
        "kind": kind,
        "media_type": media_type,
        "media_id": show.id,
        "title": show.title,
        "body": body,
        "poster_url": show.poster_url,
        "event_at": air_at,
        "dedupe_key": f"ep:{media_type}:{show.id}:{season_number or 0}:{episode_number}",
    }


@dataclass(frozen=True)
class _EpisodeSource:
    media_type: str
    show_model: type[Anime] | type[TVShow]
    season_model: type[AnimeSeason] | type[TVSeason]
    episode_model: type[AnimeEpisode] | type[TVEpisode]
    status_enum: type[AnimeStatus] | type[TVShowStatus]


_EPISODE_SOURCES = (
    _EpisodeSource("anime", Anime, AnimeSeason, AnimeEpisode, AnimeStatus),
    _EpisodeSource("tv", TVShow, TVSeason, TVEpisode, TVShowStatus),
)


async def _exact_episode_notifications(
    db: AsyncSession,
    user_id: UUID,
    prefs: dict[str, Any],
    window: tuple[int, int],
    source: _EpisodeSource,
) -> tuple[list[dict[str, Any]], set[tuple[Any, int]]]:
    """Episodes with their own exact air time establish the fallback deduplication set."""
    rows: list[dict[str, Any]] = []
    buckets = list(prefs["notify_statuses"])
    ep_stmt = (
        select(
            source.show_model,
            source.season_model.season_number,
            source.episode_model.episode_number,
            source.episode_model.air_at,
        )
        .join(source.season_model, source.season_model.show_id == source.show_model.id)
        .join(source.episode_model, source.episode_model.season_id == source.season_model.id)
        .where(
            source.show_model.user_id == user_id,
            source.show_model.deleted_at.is_(None),
            source.show_model.status.in_(tracked_statuses(source.status_enum, buckets)),
            source.episode_model.air_at.is_not(None),
            source.episode_model.air_at.between(window[0], window[1]),
        )
    )
    seen_numbers: set[tuple[Any, int]] = set()
    for show, season_number, episode_number, air_at in (await db.execute(ep_stmt)).all():
        seen_numbers.add((show.id, episode_number))
        row = _episode_row(
            source.media_type, show, season_number, episode_number, air_at, prefs=prefs
        )
        if row:
            rows.append(row)
    return rows, seen_numbers


async def _next_episode_notifications(
    db: AsyncSession,
    user_id: UUID,
    prefs: dict[str, Any],
    window: tuple[int, int],
    source: _EpisodeSource,
    *,
    seen_numbers: set[tuple[Any, int]],
) -> list[dict[str, Any]]:
    """Use a confirmed next-episode time when no timed episode row already covers it."""
    rows: list[dict[str, Any]] = []
    buckets = list(prefs["notify_statuses"])
    next_stmt = select(source.show_model).where(
        source.show_model.user_id == user_id,
        source.show_model.deleted_at.is_(None),
        source.show_model.status.in_(tracked_statuses(source.status_enum, buckets)),
        source.show_model.next_episode_air_at.is_not(None),
        source.show_model.next_episode_air_at.between(window[0], window[1]),
        source.show_model.next_episode_number.is_not(None),
    )
    # SQLAlchemy infers the shared Base for a union of model classes; this source selects shows.
    for show in cast(Sequence[Anime | TVShow], (await db.execute(next_stmt)).scalars().all()):
        number = show.next_episode_number
        air_at = show.next_episode_air_at
        if number is None or air_at is None or (show.id, number) in seen_numbers:
            continue
        season_number = max((s.season_number for s in show.seasons), default=1)
        row = _episode_row(source.media_type, show, season_number, number, air_at, prefs=prefs)
        if row:
            rows.append(row)
    return rows


async def _movie_notifications(
    db: AsyncSession, user_id: UUID, prefs: dict[str, Any], window: tuple[int, int]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    buckets = list(prefs["notify_statuses"])
    kinds_on = set(prefs["notify_media_types"])
    movie_statuses = tracked_statuses(MovieStatus, [b for b in buckets if b != "watching"])
    if prefs["notify_movie_released"] and "movie" in kinds_on and movie_statuses:
        today = date.today()
        first_day = date.fromtimestamp(window[0])
        movie_stmt = select(Movie).where(
            Movie.user_id == user_id,
            Movie.deleted_at.is_(None),
            Movie.status.in_(movie_statuses),
            Movie.release_date.is_not(None),
            Movie.release_date.between(first_day, today),
        )
        for movie in (await db.execute(movie_stmt)).scalars().all():
            if movie.release_date is None:
                continue
            rows.append(
                {
                    "kind": "movie_released",
                    "media_type": "movie",
                    "media_id": movie.id,
                    "title": movie.title,
                    "body": "Released",
                    "poster_url": movie.poster_url,
                    "event_at": _noon_utc(movie.release_date),
                    "dedupe_key": f"movie:{movie.id}",
                }
            )

    return rows


async def generate_for_user(db: AsyncSession, user_id: UUID) -> int:
    """Creates any notifications that are due. Returns how many were new."""
    prefs = await load_preferences(db, user_id)
    now = int(time.time())
    since = now - WINDOW_SECONDS
    rows: list[dict[str, Any]] = []

    # a notification older than the chosen retention is cleared (0 = keep).
    # Only ones older than the "just aired" window are removed, so a cleared
    # one can never be generated again and come straight back.
    retention_days = int(prefs["notification_retention_days"])
    if retention_days:
        cutoff = min(now - retention_days * 86400, since)
        await db.execute(
            delete(Notification).where(
                Notification.user_id == user_id, Notification.event_at < cutoff
            )
        )

    window = (since, now)
    for source in _EPISODE_SOURCES:
        if source.media_type not in prefs["notify_media_types"] or not prefs["notify_statuses"]:
            continue
        exact_rows, seen_numbers = await _exact_episode_notifications(
            db, user_id, prefs, window, source
        )
        rows.extend(exact_rows)
        rows.extend(
            await _next_episode_notifications(
                db, user_id, prefs, window, source, seen_numbers=seen_numbers
            )
        )
    rows.extend(await _movie_notifications(db, user_id, prefs, window))
    created = await _insert(db, user_id, rows)
    await db.commit()
    return created


async def record_sequel_announcements(
    db: AsyncSession,
    user_id: UUID,
    show: Anime,
    old_chain: list[dict[str, Any]] | None,
    new_chain: list[dict[str, Any]],
) -> None:
    """A finished anime whose franchise chain grew a new season since the
    last look. Only fires for a chain that was fetched before (there is a
    baseline to compare against) so the first fetch never notifies, and
    only for shows the user completed. The time is when we learned of it,
    since AniList does not say when a sequel was announced."""
    prefs = await load_preferences(db, user_id)
    if not prefs["notify_sequel_announced"] or "anime" not in prefs["notify_media_types"]:
        return
    if old_chain is None:
        return
    if show.status not in (AnimeStatus.WATCHED, AnimeStatus.FAVORITE):
        return
    known = {n["id"] for n in old_chain}
    rows: list[dict[str, Any]] = []
    for node in new_chain:
        if node["id"] in known or node.get("is_current"):
            continue
        fmt = (node.get("format") or "").lower()
        if fmt not in ("tv", "ona", "tv short"):
            continue
        rows.append(
            {
                "kind": "sequel_announced",
                "media_type": "anime",
                "media_id": show.id,
                "title": show.title,
                "body": f"A new season is listed: {node['title']}",
                "poster_url": node.get("poster_url") or show.poster_url,
                "event_at": int(time.time()),
                "dedupe_key": f"seq:{show.id}:{node['id']}",
            }
        )
    if await _insert(db, user_id, rows):
        await db.commit()
