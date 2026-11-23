"""The date and airing parts of a media smart list rule: finished or started in a
year, added lately, released between two years, still airing, and episodes that
have aired but are not watched. Each one reads a date or flag that is saved on
the title; nothing is estimated, and a title missing that date does not match."""

from __future__ import annotations

import time
from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow

_EPISODIC: dict[str, tuple[Any, Any, Any]] = {
    "tv": (TVShow, TVSeason, TVEpisode),
    "anime": (Anime, AnimeSeason, AnimeEpisode),
}


def wants_behind(rule: dict) -> bool:
    """Only a rule that asks about episodes behind needs the episode lookup."""
    return rule.get("episodes_behind") is not None


async def shows_behind(db: AsyncSession, media_type: str, user_id: UUID) -> set[UUID]:
    """Shows with at least one episode that has aired and is not watched. An
    episode counts as aired by its exact air time, or by its air date when
    that is all there is."""
    models = _EPISODIC.get(media_type)
    if models is None:
        return set()
    show, season, episode = models
    now, today = int(time.time()), date.today()
    rows = await db.execute(
        select(season.show_id)
        .join(episode, episode.season_id == season.id)
        .join(show, show.id == season.show_id)
        .where(
            show.user_id == user_id,
            show.deleted_at.is_(None),
            episode.watched.is_(False),
            or_(
                episode.air_at <= now,
                and_(episode.air_at.is_(None), episode.air_date <= today),
            ),
        )
        .distinct()
    )
    return set(rows.scalars().all())


def _released(media: Any, media_type: str) -> date | None:
    return media.release_date if media_type == "movie" else media.first_air_date


def matches(media: Any, media_type: str, rule: dict, behind: set[UUID]) -> bool:
    """Whether a title passes every date and airing condition the rule sets."""
    checks = (
        ("finished_year", lambda year: media.end_date is not None and media.end_date.year == year),
        (
            "started_year",
            lambda year: media.start_date is not None and media.start_date.year == year,
        ),
        (
            "added_within_days",
            lambda days: (media.created_at or 0) >= time.time() - days * 86400,
        ),
        (
            "released_from",
            lambda year: (d := _released(media, media_type)) is not None and d.year >= year,
        ),
        (
            "released_to",
            lambda year: (d := _released(media, media_type)) is not None and d.year <= year,
        ),
        # a movie never airs, so asking for airing titles leaves movies out
        ("airing", lambda want: media_type != "movie" and bool(media.is_airing) == want),
        (
            "episodes_behind",
            lambda want: media_type != "movie" and (media.id in behind) == want,
        ),
    )
    return all(rule.get(key) is None or check(rule[key]) for key, check in checks)
