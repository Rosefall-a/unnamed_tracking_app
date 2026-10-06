"""Library statistics for the Statistics page: one payload with an
Overview, Games, Movies, TV and Anime section.

Everything here is exact or absent, never estimated. Watch time is the
sum of the runtimes the providers gave for the episodes and movies you
actually watched; a title or episode with no runtime on record is counted
and reported as "no runtime data" instead of being given a made-up
number. Game time is the playtime the game platforms reported."""

from collections import Counter
from contextvars import ContextVar
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, NamedTuple, TypedDict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import coalesce as sql_coalesce
from sqlalchemy.sql.functions import count as sql_count
from sqlalchemy.sql.functions import sum as sql_sum

from src.core.auth import get_current_user
from src.core.preferences import load_preferences
from src.core.titles import display_title
from src.database.models.achievement import Achievement
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason
from src.database.models.game import Game, GameStatus
from src.database.models.media_extras import ActivityEventType, ActivityLog, MediaType, RewatchLog
from src.database.models.movies import Movie
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow
from src.database.models.user import User
from src.database.session import get_db
from src.features.game_stats import game_stats

router = APIRouter(
    prefix="/api/media-stats", tags=["stats"], dependencies=[Depends(get_current_user)]
)

_BUCKET = {
    "WISHLIST": "plan",
    "WATCHLIST": "plan",
    "BACKLOG": "hold",
    "IN_PROGRESS": "watching",
    "REWATCH": "watching",
    "WATCHED": "completed",
    "FAVORITE": "completed",
    "DROPPED": "dropped",
    # games
    "ON_HOLD": "hold",
    "PLAYING": "watching",
    "PLAYED": "completed",
    "BEATEN": "completed",
    "MASTERED": "completed",
}
_BUCKETS = ("plan", "hold", "watching", "completed", "dropped")


# the viewer's title language for the request being built, so the many row
# builders below need no extra parameter
_language: ContextVar[str] = ContextVar("stats_title_language", default="english")


def _t(item: Any) -> str:
    return display_title(item, _language.get())


def _hours_label(seconds: int) -> str:
    hours, minutes = divmod(seconds // 60, 60)
    return f"{hours}h {minutes}m played" if hours else f"{minutes}m played"


def _status(value: Any) -> str:
    return getattr(value, "value", str(value))


def _bucket_counts(items: list[Any]) -> dict[str, int]:
    counts = Counter(_BUCKET.get(_status(i.status), "plan") for i in items)
    return {b: counts.get(b, 0) for b in _BUCKETS}


def _score(v: Decimal | None) -> float | None:
    return None if v is None else float(v)


def _score_stats(items: list[Any]) -> dict[str, Any]:
    scores = [s for s in (_score(i.rating_overall) for i in items) if s is not None]
    distribution = {str(n): 0 for n in range(1, 11)}
    for s in scores:
        distribution[str(min(10, max(1, int(s + 0.5))))] += 1
    return {
        "rated": len(scores),
        "average": round(sum(scores) / len(scores), 2) if scores else None,
        "distribution": distribution,
    }


def _top(counter: Counter, n: int = 10) -> list[dict[str, Any]]:
    return [{"name": k, "count": v} for k, v in counter.most_common(n) if k]


def _genre_rows(items: list[Any], field: str = "genres", n: int = 10) -> list[dict[str, Any]]:
    counts: Counter = Counter()
    sums: dict[str, list[float]] = {}
    for i in items:
        s = _score(getattr(i, "rating_overall", None))
        for g in getattr(i, field) or []:
            counts[g] += 1
            if s is not None:
                sums.setdefault(g, []).append(s)
    return [
        {
            "name": g,
            "count": c,
            "average": round(sum(sums[g]) / len(sums[g]), 2) if g in sums else None,
        }
        for g, c in counts.most_common(n)
    ]


def _by_year(items: list[Any], field: str) -> list[dict[str, Any]]:
    years = Counter(getattr(i, field).year for i in items if getattr(i, field, None))
    return [{"year": y, "count": c} for y, c in sorted(years.items())]


def _poster(item: Any) -> str | None:
    if isinstance(item, Game):
        return f"/api/game/{item.id}/assets/key_art"
    return getattr(item, "poster_url", None)


def _top_rated(items: list[Any], n: int = 10, kind: str = "") -> list[dict[str, Any]]:
    rated = [i for i in items if i.rating_overall is not None]
    rated.sort(key=lambda i: float(i.rating_overall), reverse=True)
    return [
        {
            "id": str(i.id),
            "title": _t(i),
            "score": float(i.rating_overall),
            "poster_url": _poster(i),
            "kind": kind,
        }
        for i in rated[:n]
    ]


def _added_per_month(items: list[Any], months: int = 12) -> list[dict[str, Any]]:
    today = date.today()
    keys = []
    y, m = today.year, today.month
    for _ in range(months):
        keys.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    keys.reverse()
    counts = Counter(date.fromtimestamp(i.created_at).strftime("%Y-%m") for i in items)
    return [{"month": k, "count": counts.get(k, 0)} for k in keys]


class SeasonEpisodeRow(NamedTuple):
    season_id: Any
    show_id: Any
    expected: int | None
    counter: int | None
    total_rows: int
    flagged_rows: int
    flagged_minutes: int
    flagged_unknown: int


class EpisodeCounts(TypedDict):
    watched: int
    total: int
    minutes: int
    unknown: int


def _season_counts(
    row: SeasonEpisodeRow,
    show_runtime: int | None,
    legacy_rows: list[tuple[int, int | None]],
) -> EpisodeCounts:
    counter = row.counter or 0
    minutes = int(row.flagged_minutes)
    unknown = row.flagged_unknown
    unbacked = counter - row.flagged_rows
    if unbacked > 0:
        for _number, runtime in legacy_rows[:unbacked]:
            if runtime:
                minutes += runtime
            else:
                unknown += 1
            unbacked -= 1
        # Progress with no episode row on record uses only a known show runtime.
        if unbacked > 0:
            if show_runtime:
                minutes += unbacked * show_runtime
            else:
                unknown += unbacked
    return {
        "watched": max(row.flagged_rows, counter),
        "total": max(row.total_rows, row.expected or 0),
        "minutes": minutes,
        "unknown": unknown,
    }


def _episode_summary(counts: dict[Any, EpisodeCounts], by_show: dict[Any, Any]) -> dict[str, Any]:
    watched_first = minutes_first = without_runtime = watched_again = minutes_again = 0
    ranked: list[dict[str, Any]] = []
    for show_id, c in counts.items():
        again = by_show[show_id].rewatches or 0
        watched_first += c["watched"]
        minutes_first += c["minutes"]
        without_runtime += c["unknown"]
        watched_again += c["watched"] * again
        minutes_again += c["minutes"] * again
        if c["watched"]:
            ranked.append(
                {
                    "id": str(show_id),
                    "title": _t(by_show[show_id]),
                    "minutes": c["minutes"] * (1 + again),
                    "episodes": c["watched"] * (1 + again),
                }
            )
    ranked.sort(key=lambda r: r["minutes"], reverse=True)
    return {
        "episodes_watched": watched_first,
        "episodes_rewatched": watched_again,
        "minutes_first": minutes_first,
        "minutes_rewatch": minutes_again,
        "minutes_watched": minutes_first + minutes_again,
        "episodes_without_runtime": without_runtime,
        "most_watched": ranked[:10],
        "_progress": {
            str(k): {"watched": v["watched"], "total": v["total"]} for k, v in counts.items()
        },
    }


async def _episode_rows(
    db: AsyncSession, show_model: Any, season_model: Any, ep_model: Any, *, user_id: Any
) -> tuple[Any, dict[Any, list[tuple[int, int | None]]]]:
    runtime = sql_coalesce(ep_model.runtime_minutes, show_model.episode_runtime_minutes)
    flagged = ep_model.watched.is_(True)
    season_rows = (
        await db.execute(
            select(
                season_model.id,
                season_model.show_id,
                season_model.episode_count,
                season_model.episodes_watched,
                sql_count(ep_model.id),
                sql_count(ep_model.id).filter(flagged),
                sql_coalesce(sql_sum(runtime).filter(flagged), 0),
                sql_count(ep_model.id).filter(flagged, runtime.is_(None)),
            )
            .select_from(season_model)
            .join(show_model, show_model.id == season_model.show_id)
            .outerjoin(ep_model, ep_model.season_id == season_model.id)
            .where(show_model.user_id == user_id, show_model.deleted_at.is_(None))
            .group_by(
                season_model.id,
                season_model.show_id,
                season_model.episode_count,
                season_model.episodes_watched,
            )
        )
    ).all()

    # Progress the counter holds that no flag accounts for (older data
    # tracked by number only) is the lowest-numbered unflagged episodes, so
    # those rows are read for their own runtimes.
    legacy = {row[0]: row for row in season_rows if (row[3] or 0) > row[5]}
    legacy_rows: dict[Any, list[tuple[int, int | None]]] = {}
    if legacy:
        ep_rows = (
            await db.execute(
                select(ep_model.season_id, ep_model.episode_number, runtime)
                .select_from(ep_model)
                .join(season_model, season_model.id == ep_model.season_id)
                .join(show_model, show_model.id == season_model.show_id)
                .where(ep_model.season_id.in_(list(legacy)), ep_model.watched.is_(False))
                .order_by(ep_model.season_id, ep_model.episode_number)
            )
        ).all()
        for season_id, number, rt in ep_rows:
            legacy_rows.setdefault(season_id, []).append((number, rt))

    return season_rows, legacy_rows


async def _episode_stats(
    db: AsyncSession,
    show_model: Any,
    season_model: Any,
    ep_model: Any,
    *,
    user_id: Any,
    shows: list[Any],
) -> dict[str, Any]:
    """What was actually watched, from both places the app records it.

    A season keeps a progress counter (`episodes_watched`, what the library
    list shows and what "advance episode" moves) and each episode row has
    its own watched flag. Most history lives in the counter, so an episode
    counts as watched when its row is flagged OR its number is within the
    season's counter. Counter episodes with no row on record are counted
    too, at the show's own episode runtime; if the show has none they are
    reported as "no runtime on record", never guessed.

    Each rewatch of a title repeats that title's watched episodes once. A
    season is completed only when every one of its episodes is watched
    (against the larger of the rows on record and the known total), so a
    half-finished season never shows up as a finished one."""
    season_rows, legacy_rows = await _episode_rows(
        db, show_model, season_model, ep_model, user_id=user_id
    )
    return _episode_counts(season_rows, legacy_rows, {show.id: show for show in shows})


def _episode_counts(
    season_rows: Any,
    legacy_rows: dict[Any, list[tuple[int, int | None]]],
    by_show: dict[Any, Any],
) -> dict[str, Any]:
    counts: dict[Any, EpisodeCounts] = {}
    seasons_completed = seasons_in_progress = known = 0
    for values in season_rows:
        row = SeasonEpisodeRow(*values)
        show = by_show.get(row.show_id)
        if show is None:  # filtered out (Plan to Watch hidden in Statistics)
            continue
        season_counts = _season_counts(
            row, show.episode_runtime_minutes, legacy_rows.get(row.season_id, [])
        )
        known += season_counts["total"]
        if season_counts["total"] and season_counts["watched"] >= season_counts["total"]:
            seasons_completed += 1
        elif season_counts["watched"]:
            seasons_in_progress += 1
        c = counts.setdefault(row.show_id, {"watched": 0, "total": 0, "minutes": 0, "unknown": 0})
        c["watched"] += season_counts["watched"]
        c["total"] += season_counts["total"]
        c["minutes"] += season_counts["minutes"]
        c["unknown"] += season_counts["unknown"]

    return {
        **_episode_summary(counts, by_show),
        "episodes_known": known,
        "seasons_completed": seasons_completed,
        "seasons_in_progress": seasons_in_progress,
    }


async def _rewatch_counts(db: AsyncSession, user_id: Any, media_type: str) -> int:
    return (
        await db.scalar(
            select(sql_count())
            .select_from(RewatchLog)
            .where(RewatchLog.user_id == user_id, RewatchLog.media_type == MediaType(media_type))
        )
        or 0
    )


def _most_rewatched(items: list[Any], n: int = 5) -> list[dict[str, Any]]:
    again = [i for i in items if (i.rewatches or 0) > 0]
    again.sort(key=lambda i: i.rewatches, reverse=True)
    return [{"id": str(i.id), "title": _t(i), "count": i.rewatches} for i in again[:n]]


def _episodic_section(
    shows: list[Any], episodes: dict[str, Any], rewatch_logs: int, studios_field: str, kind: str
) -> dict[str, Any]:
    studios: Counter = Counter()
    for s in shows:
        studios.update(getattr(s, studios_field) or [])
    formats = (
        Counter(getattr(s, "format", None) for s in shows)
        if shows and hasattr(shows[0], "format")
        else Counter()
    )
    return {
        "titles": len(shows),
        "by_status": _bucket_counts(shows),
        "favorites": sum(1 for s in shows if s.favorite),
        "score": _score_stats(shows),
        "genres": _genre_rows(shows),
        "by_release_year": _by_year(shows, "first_air_date"),
        "top_rated": _top_rated(shows, kind=kind),
        "added_per_month": _added_per_month(shows),
        "studios": _top(studios),
        "formats": _top(formats),
        "rewatch_logs": rewatch_logs,
        "most_rewatched": _most_rewatched(shows),
        **{k: v for k, v in episodes.items() if not k.startswith("_")},
    }


def _movie_section(movies: list[Movie], rewatch_logs: int) -> dict[str, Any]:
    seen = [
        m
        for m in movies
        if _BUCKET.get(_status(m.status)) == "completed" or _status(m.status) == "REWATCH"
    ]
    with_runtime = [m for m in seen if m.runtime_minutes]
    minutes_first = sum(m.runtime_minutes or 0 for m in with_runtime)
    minutes_again = sum((m.runtime_minutes or 0) * (m.rewatches or 0) for m in with_runtime)
    minutes = minutes_first + minutes_again
    directors: Counter = Counter(m.director for m in movies if m.director)
    studios: Counter = Counter()
    for m in movies:
        studios.update(m.studios or [])
    return {
        "titles": len(movies),
        "by_status": _bucket_counts(movies),
        "favorites": sum(1 for m in movies if m.favorite),
        "score": _score_stats(movies),
        "genres": _genre_rows(movies),
        "by_release_year": _by_year(movies, "release_date"),
        "top_rated": _top_rated(movies, kind="movie"),
        "added_per_month": _added_per_month(movies),
        "studios": _top(studios),
        "directors": _top(directors),
        "movies_watched": len(seen),
        "minutes_watched": int(minutes),
        "minutes_first": int(minutes_first),
        "minutes_rewatch": int(minutes_again),
        "movies_without_runtime": len(seen) - len(with_runtime),
        "rewatches": sum(m.rewatches or 0 for m in movies),
        "most_rewatched": _most_rewatched(movies),
        "rewatch_logs": rewatch_logs,
    }


async def _games_section(
    db: AsyncSession, user_id: Any, include_plan: bool = True
) -> dict[str, Any]:
    games = list(
        (await db.execute(select(Game).where(Game.user_id == user_id, Game.deleted_at.is_(None))))
        .scalars()
        .all()
    )
    if not include_plan:
        games = [g for g in games if _BUCKET.get(_status(g.status), "plan") != "plan"]
    unlocked, total = (
        await db.execute(
            select(
                sql_count().filter(Achievement.unlocked.is_(True)),
                sql_count(),
            )
            .select_from(Achievement)
            .join(Game, Game.id == Achievement.game_id)
            .where(Game.user_id == user_id, Game.deleted_at.is_(None))
        )
    ).one()
    per_game = {
        gid: (int(u), int(n))
        for gid, u, n in (
            await db.execute(
                select(
                    Achievement.game_id,
                    sql_count().filter(Achievement.unlocked.is_(True)),
                    sql_count(),
                )
                .join(Game, Game.id == Achievement.game_id)
                .where(Game.user_id == user_id, Game.deleted_at.is_(None))
                .group_by(Achievement.game_id)
            )
        ).all()
    }
    tags: Counter = Counter()
    for g in games:
        tags.update(g.tags or [])
    spent: dict[str, float] = {}
    for g in games:
        if g.purchase_price is not None:
            code = g.purchase_price_currency_code or "?"
            spent[code] = round(spent.get(code, 0.0) + float(g.purchase_price), 2)
    finished_years = Counter(
        date.fromtimestamp(g.completion_date).year for g in games if g.completion_date
    )
    by_playtime = sorted(
        (g for g in games if g.playtime_seconds), key=lambda g: g.playtime_seconds, reverse=True
    )
    return {
        "titles": len(games),
        "by_status": _bucket_counts(games),
        "favorites": sum(1 for g in games if g.favorite),
        "score": _score_stats(games),
        "playtime_seconds": sum(g.playtime_seconds or 0 for g in games),
        "games_with_playtime": len(by_playtime),
        "most_played": [
            {"id": str(g.id), "title": g.title, "seconds": g.playtime_seconds}
            for g in by_playtime[:10]
        ],
        "achievements_unlocked": unlocked,
        "achievements_total": total,
        "sources": _top(Counter(g.source for g in games)),
        "developers": _top(Counter(g.developer for g in games)),
        "tags": _top(tags),
        "by_release_year": _by_year(games, "release_date"),
        "finished_per_year": [{"year": y, "count": c} for y, c in sorted(finished_years.items())],
        "top_rated": _top_rated(games, kind="game"),
        "added_per_month": _added_per_month(games),
        "spent": [{"currency": k, "amount": v} for k, v in sorted(spent.items())],
        "insights": game_stats(games, per_game, datetime.now()),
    }


def _activity_streaks(all_days: set[date]) -> tuple[int, int]:
    longest = run = 0
    previous = None
    for d in sorted(all_days):
        run = run + 1 if previous and d - previous == timedelta(days=1) else 1
        longest = max(longest, run)
        previous = d
    current = 0
    cursor = date.today() if date.today() in all_days else date.today() - timedelta(days=1)
    while cursor in all_days:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


async def _activity_section(db: AsyncSession, user_id: Any) -> dict[str, Any]:
    """Per-day episode counts for the heatmap plus streaks, from the
    history log (exact: it records what was checked off, and when)."""
    since = date.today() - timedelta(days=364)
    rows = (
        await db.execute(
            select(ActivityLog.event_date, sql_sum(ActivityLog.count))
            .where(
                ActivityLog.user_id == user_id,
                ActivityLog.event_type == ActivityEventType.EPISODES_WATCHED,
                ActivityLog.event_date >= since,
            )
            .group_by(ActivityLog.event_date)
        )
    ).all()
    episodes_per_day = {d: int(c) for d, c in rows}
    unlocked_ts = (
        (
            await db.execute(
                select(Achievement.unlocked_at)
                .join(Game, Game.id == Achievement.game_id)
                .where(
                    Game.user_id == user_id,
                    Game.deleted_at.is_(None),
                    Achievement.unlocked.is_(True),
                    Achievement.unlocked_at.is_not(None),
                )
            )
        )
        .scalars()
        .all()
    )
    unlocked_days = Counter(date.fromtimestamp(ts) for ts in unlocked_ts if ts is not None)
    per_day = {
        d: episodes_per_day.get(d, 0) + n
        for d in set(episodes_per_day) | {d for d in unlocked_days if d >= since}
        for n in [unlocked_days.get(d, 0)]
    }
    all_days = set(unlocked_days) | {
        d
        for (d,) in (
            await db.execute(
                select(ActivityLog.event_date).where(ActivityLog.user_id == user_id).distinct()
            )
        ).all()
    }
    current, longest = _activity_streaks(all_days)
    busiest = max(per_day.items(), key=lambda kv: kv[1], default=None)
    return {
        "per_day": [
            {
                "date": d.isoformat(),
                "count": c,
                "episodes": episodes_per_day.get(d, 0),
                "achievements": unlocked_days.get(d, 0),
            }
            for d, c in sorted(per_day.items())
        ],
        "active_days_total": len(all_days),
        "current_streak": current,
        "longest_streak": longest,
        "busiest_day": {
            "date": busiest[0].isoformat(),
            "count": busiest[1],
            "episodes": episodes_per_day.get(busiest[0], 0),
            "achievements": unlocked_days.get(busiest[0], 0),
        }
        if busiest
        else None,
    }


def _watching_now(
    items: list[Any], progress: dict[str, dict[str, int]], kind: str
) -> list[dict[str, Any]]:
    rows = []
    for i in items:
        if _BUCKET.get(_status(i.status)) != "watching":
            continue
        p = progress.get(str(i.id), {"watched": 0, "total": 0})
        rows.append(
            {
                "id": str(i.id),
                "title": _t(i),
                "kind": kind,
                "watched": p["watched"],
                "total": p["total"],
                "poster_url": i.poster_url,
                "updated_at": i.updated_at,
            }
        )
    return rows


def _unrated_completed(items: list[Any], kind: str) -> list[dict[str, Any]]:
    return [
        {"id": str(i.id), "title": _t(i), "kind": kind, "poster_url": _poster(i)}
        for i in items
        if _BUCKET.get(_status(i.status)) == "completed" and i.rating_overall is None
    ]


async def _playing_rows(db: AsyncSession, user_id: Any) -> list[dict[str, Any]]:
    playing = list(
        (
            await db.execute(
                select(Game)
                .where(
                    Game.user_id == user_id,
                    Game.deleted_at.is_(None),
                    Game.status == GameStatus.PLAYING,
                )
                .order_by(Game.last_played_at.desc().nulls_last(), Game.updated_at.desc())
                .limit(12)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": str(g.id),
            "title": g.title,
            "kind": "game",
            "watched": 0,
            "total": 0,
            "poster_url": _poster(g),
            "label": _hours_label(g.playtime_seconds)
            if g.playtime_seconds
            else "No playtime recorded",
        }
        for g in playing
    ]


def _overview_section(
    sections: dict[str, dict[str, Any]],
    *,
    in_progress: list[dict[str, Any]],
    needs_score: dict[str, Any],
    activity: dict[str, Any],
) -> dict[str, Any]:
    media_minutes = (
        sections["movie"]["minutes_watched"]
        + sections["tv"]["minutes_watched"]
        + sections["anime"]["minutes_watched"]
    )
    every_top = (
        sections["movie"]["top_rated"]
        + sections["tv"]["top_rated"]
        + sections["anime"]["top_rated"]
        + sections["game"]["top_rated"]
    )
    every_top.sort(key=lambda t: t["score"], reverse=True)
    return {
        "kinds": [
            {
                "kind": "movie",
                "titles": sections["movie"]["titles"],
                "completed": sections["movie"]["by_status"]["completed"],
                "minutes": sections["movie"]["minutes_watched"],
            },
            {
                "kind": "tv",
                "titles": sections["tv"]["titles"],
                "completed": sections["tv"]["by_status"]["completed"],
                "minutes": sections["tv"]["minutes_watched"],
            },
            {
                "kind": "anime",
                "titles": sections["anime"]["titles"],
                "completed": sections["anime"]["by_status"]["completed"],
                "minutes": sections["anime"]["minutes_watched"],
            },
            {
                "kind": "game",
                "titles": sections["game"]["titles"],
                "completed": sections["game"]["by_status"]["completed"],
                "minutes": sections["game"]["playtime_seconds"] // 60,
            },
        ],
        "media_minutes": media_minutes,
        "game_seconds": sections["game"]["playtime_seconds"],
        "media_titles": sections["movie"]["titles"]
        + sections["tv"]["titles"]
        + sections["anime"]["titles"],
        "media_completed": (
            sections["movie"]["by_status"]["completed"]
            + sections["tv"]["by_status"]["completed"]
            + sections["anime"]["by_status"]["completed"]
        ),
        "media_favorites": sections["movie"]["favorites"]
        + sections["tv"]["favorites"]
        + sections["anime"]["favorites"],
        "top_rated": every_top[:10],
        "in_progress": in_progress[:16],
        "backlog": [
            {"kind": kind, "waiting": sec["by_status"]["plan"], "on_hold": sec["by_status"]["hold"]}
            for kind, sec in (
                ("movie", sections["movie"]),
                ("tv", sections["tv"]),
                ("anime", sections["anime"]),
                ("game", sections["game"]),
            )
        ],
        "game_backlog": sections["game"]["insights"]["backlog"],
        "games_finished_this_year": sections["game"]["insights"]["finished_this_year"],
        "score_by_type": [
            {"kind": k, "average": sec["score"]["average"], "rated": sec["score"]["rated"]}
            for k, sec in (
                ("movie", sections["movie"]),
                ("tv", sections["tv"]),
                ("anime", sections["anime"]),
                ("game", sections["game"]),
            )
        ],
        "needs_score": needs_score,
        "activity": activity,
    }


async def _library_items(
    db: AsyncSession, model: Any, user_id: Any, include_plan: bool
) -> list[Any]:
    items = list(
        (
            await db.execute(
                select(model).where(model.user_id == user_id, model.deleted_at.is_(None))
            )
        )
        .scalars()
        .all()
    )
    if include_plan:
        return items
    return [item for item in items if _BUCKET.get(_status(item.status), "plan") != "plan"]


def _needs_score(movies: list[Any], tv: list[Any], anime: list[Any]) -> dict[str, Any]:
    items = (
        _unrated_completed(movies, "movie")
        + _unrated_completed(tv, "tv")
        + _unrated_completed(anime, "anime")
    )
    return {"count": len(items), "items": items[:8]}


@router.get("")
async def get_media_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict[str, Any]:
    uid = current_user.id
    prefs = await load_preferences(db, uid)
    include_plan = bool(prefs["stats_include_plan"])
    _language.set(str(prefs["title_language"]))

    movies = await _library_items(db, Movie, uid, include_plan)
    tv = await _library_items(db, TVShow, uid, include_plan)
    anime = await _library_items(db, Anime, uid, include_plan)

    sections = {"movie": _movie_section(movies, await _rewatch_counts(db, uid, "movie"))}
    episodes = {
        "tv": await _episode_stats(db, TVShow, TVSeason, TVEpisode, user_id=uid, shows=tv),
        "anime": await _episode_stats(
            db, Anime, AnimeSeason, AnimeEpisode, user_id=uid, shows=anime
        ),
    }
    sections["tv"] = _episodic_section(
        tv, episodes["tv"], await _rewatch_counts(db, uid, "tv"), "creators", "tv"
    )
    sections["anime"] = _episodic_section(
        anime, episodes["anime"], await _rewatch_counts(db, uid, "anime"), "studios", "anime"
    )

    in_progress = _watching_now(anime, episodes["anime"]["_progress"], "anime") + _watching_now(
        tv, episodes["tv"]["_progress"], "tv"
    )
    in_progress.sort(key=lambda r: r["updated_at"], reverse=True)
    for r in in_progress:
        r.pop("updated_at")
    sections["game"] = await _games_section(db, uid, include_plan)
    playing_rows = await _playing_rows(db, uid)

    overview = _overview_section(
        sections,
        in_progress=in_progress + playing_rows,
        needs_score=_needs_score(movies, tv, anime),
        activity=await _activity_section(db, uid),
    )
    return {
        "overview": overview,
        "games": sections["game"],
        "movie": sections["movie"],
        "tv": sections["tv"],
        "anime": sections["anime"],
    }
