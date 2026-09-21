"""The numbers this app must get exactly right: watch time, completed
seasons, rewatches, notification content and deduplication, status labels
in history, preferences validation, and ani.zip parsing.

Database tests build their own user and titles and delete that user (which
cascades to everything it made) when they finish, so they leave nothing
behind and never touch real data. Run inside the backend container:
    docker compose exec -e PYTHONPATH=/app backend python -m pytest /app/tests -q
"""

import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import delete, select

from src.api.routes.media_extras import status_change_detail
from src.api.routes.media_stats import _bucket_counts, _score_stats, get_media_stats
from src.core.preferences import DEFAULTS, validate_preference
from src.database.models.anime import Anime, AnimeEpisode, AnimeSeason, AnimeStatus
from src.database.models.movies import Movie, MovieStatus
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features.metadata.anime.anizip import AniZipClient
from src.features.notifications import _episode_row, generate_for_user


# ---------------------------------------------------------------- pure logic
def test_status_change_uses_the_names_shown_in_the_app():
    assert (
        status_change_detail(AnimeStatus.WISHLIST, AnimeStatus.IN_PROGRESS)
        == "Plan to Watch → Watching"
    )
    assert (
        status_change_detail(AnimeStatus.IN_PROGRESS, AnimeStatus.WATCHED) == "Watching → Completed"
    )


def test_status_change_between_equivalent_statuses_is_not_recorded():
    # Wishlist and Watchlist are both "Plan to Watch" to the user
    assert status_change_detail(AnimeStatus.WISHLIST, AnimeStatus.WATCHLIST) is None


def test_preferences_reject_unknown_keys_and_bad_values():
    assert validate_preference("calendar_game_releases", True) is True
    with pytest.raises(ValueError):
        validate_preference("no_such_setting", True)
    with pytest.raises(ValueError):
        validate_preference("calendar_game_releases", "yes")
    with pytest.raises(ValueError):
        validate_preference("calendar_week_start", 3)
    with pytest.raises(ValueError):
        validate_preference("notification_retention_days", 45)
    assert validate_preference("notification_retention_days", 0) == 0


def test_every_default_passes_its_own_validation():
    for key, value in DEFAULTS.items():
        assert validate_preference(key, value) == value


class _Item:
    def __init__(self, status, score=None):
        self.status = status
        self.rating_overall = score


def test_status_buckets_group_the_eight_statuses_into_five():
    items = [
        _Item(AnimeStatus.WISHLIST),
        _Item(AnimeStatus.WATCHLIST),
        _Item(AnimeStatus.WATCHED),
        _Item(AnimeStatus.FAVORITE),
    ]
    counts = _bucket_counts(items)
    assert counts["plan"] == 2
    assert counts["completed"] == 2
    assert counts["watching"] == counts["hold"] == counts["dropped"] == 0


def test_score_stats_average_and_distribution():
    from decimal import Decimal

    stats = _score_stats(
        [
            _Item(AnimeStatus.WATCHED, Decimal("8")),
            _Item(AnimeStatus.WATCHED, Decimal("9")),
            _Item(AnimeStatus.WATCHED, None),
        ]
    )
    assert stats["rated"] == 2
    assert stats["average"] == 8.5
    assert stats["distribution"]["8"] == 1 and stats["distribution"]["9"] == 1


class _Show:
    id = uuid.uuid4()
    title = "Test Show"
    poster_url = None


def test_first_episode_is_a_season_start_and_later_ones_are_episodes():
    prefs = dict(DEFAULTS)
    first = _episode_row("anime", _Show(), 1, 1, 1_700_000_000, prefs)
    later = _episode_row("anime", _Show(), 1, 5, 1_700_000_000, prefs)
    assert first and first["kind"] == "season_started"
    assert later and later["kind"] == "episode_aired" and later["body"] == "Episode 5 aired"
    assert later["event_at"] == 1_700_000_000  # the exact time, untouched


def test_tv_later_seasons_name_the_season():
    row = _episode_row("tv", _Show(), 3, 4, 1_700_000_000, dict(DEFAULTS))
    assert row and row["body"] == "Season 3 episode 4 aired"


def test_notification_toggles_switch_each_kind_off():
    prefs = {**DEFAULTS, "notify_episode_aired": False}
    assert _episode_row("anime", _Show(), 1, 5, 1, prefs) is None
    assert _episode_row("anime", _Show(), 1, 1, 1, prefs) is not None
    prefs = {**DEFAULTS, "notify_season_started": False}
    assert _episode_row("anime", _Show(), 1, 1, 1, prefs) is None


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self, payload):
        self.payload = payload

    def get(self, *args, **kwargs):
        return _FakeResponse(self.payload)


def test_anizip_keeps_only_this_entrys_numbered_episodes_and_parses_air_time():
    payload = {
        "episodeCount": 2,
        "episodes": {
            "1": {
                "title": {"en": "The Journey`s End"},
                "overview": "Intro.\nSource: X",
                "image": "http://img/1.jpg",
                "airDate": "2023-09-29",
                "airDateUtc": "2023-09-29T14:00:00Z",
                "runtime": 26,
            },
            "2": {"title": {"en": "Second"}, "runtime": 0},
            "3": {"title": {"en": "belongs to a later season"}},
            "S1": {"title": {"en": "special"}},
        },
    }
    episodes = AniZipClient(session=_FakeSession(payload)).episodes("1")  # type: ignore[arg-type]
    assert [e["episode_number"] for e in episodes] == [1, 2]
    first = episodes[0]
    assert first["title"] == "The Journey's End"
    assert first["description"] == "Intro."
    assert first["still_url"] == "http://img/1.jpg"
    assert first["air_at"] == int(datetime(2023, 9, 29, 14, 0, tzinfo=timezone.utc).timestamp())
    assert first["runtime_minutes"] == 26
    assert episodes[1]["runtime_minutes"] is None  # a runtime of 0 is "unknown", not zero minutes


# ------------------------------------------------------- database, rolled back
async def _user(db):
    user = User(
        username=f"t_{uuid.uuid4().hex[:10]}",
        email=f"{uuid.uuid4().hex[:10]}@example.test",
        password_hash="x",
    )
    db.add(user)
    await db.flush()
    # a plain attribute: a mapped one expires at commit and can't be re-read
    # here (generating notifications commits)
    user.scratch_id = user.id  # type: ignore[attr-defined]
    return user


async def _cleanup(db, user):
    """Undo everything a test did. Most tests never commit and a rollback is
    enough, but generating notifications commits, so the scratch user (and,
    by cascade, all its titles and notifications) is deleted outright."""
    await db.rollback()
    await db.execute(delete(User).where(User.id == user.scratch_id))
    await db.commit()


def _anime(user, title="Test Anime", status=AnimeStatus.IN_PROGRESS, rewatches=0, runtime=24):
    return Anime(
        user_id=user.scratch_id,
        title=title,
        sort_title=title.lower(),
        status=status,
        rewatches=rewatches,
        episode_runtime_minutes=runtime,
        studios=[],
        countries=[],
        languages=[],
        genres=[],
        tags=[],
        features=[],
        locked_fields=[],
    )


@pytest.mark.asyncio
async def test_only_watched_episodes_count_and_half_a_season_is_not_completed():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user)
            db.add(show)
            await db.flush()
            done = AnimeSeason(show_id=show.id, season_number=1, episode_count=4)
            half = AnimeSeason(show_id=show.id, season_number=2, episode_count=4)
            db.add_all([done, half])
            await db.flush()
            db.add_all(
                [
                    AnimeEpisode(season_id=done.id, episode_number=n, watched=True)
                    for n in range(1, 5)
                ]
                + [
                    AnimeEpisode(season_id=half.id, episode_number=n, watched=(n <= 2))
                    for n in range(1, 5)
                ]
            )
            await db.flush()

            anime = (await get_media_stats(db, user))["anime"]
            assert anime["episodes_watched"] == 6  # 4 + 2, the unwatched two are not counted
            assert anime["minutes_watched"] == 6 * 24
            assert anime["seasons_completed"] == 1  # the half-watched season is not a finished one
            assert anime["seasons_in_progress"] == 1
            assert anime["episodes_rewatched"] == 0
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_each_rewatch_adds_the_watched_episodes_again_and_nothing_more():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user, rewatches=2)
            db.add(show)
            await db.flush()
            season = AnimeSeason(show_id=show.id, season_number=1, episode_count=4)
            db.add(season)
            await db.flush()
            # only 3 of 4 watched: a rewatch multiplies what was actually watched
            db.add_all(
                [
                    AnimeEpisode(season_id=season.id, episode_number=n, watched=(n <= 3))
                    for n in range(1, 5)
                ]
            )
            await db.flush()

            anime = (await get_media_stats(db, user))["anime"]
            assert anime["episodes_watched"] == 3
            assert anime["episodes_rewatched"] == 6
            assert anime["minutes_first"] == 3 * 24
            assert anime["minutes_rewatch"] == 6 * 24
            assert anime["minutes_watched"] == 9 * 24
            assert anime["seasons_completed"] == 0
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_an_episode_with_no_runtime_is_reported_not_guessed():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user, runtime=None)
            db.add(show)
            await db.flush()
            season = AnimeSeason(show_id=show.id, season_number=1, episode_count=2)
            db.add(season)
            await db.flush()
            db.add_all(
                [
                    AnimeEpisode(
                        season_id=season.id, episode_number=1, watched=True, runtime_minutes=20
                    ),
                    AnimeEpisode(
                        season_id=season.id, episode_number=2, watched=True, runtime_minutes=None
                    ),
                ]
            )
            await db.flush()

            anime = (await get_media_stats(db, user))["anime"]
            assert anime["episodes_watched"] == 2
            assert anime["minutes_watched"] == 20  # only the known runtime is added
            assert anime["episodes_without_runtime"] == 1
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_movie_time_is_runtime_once_plus_each_rewatch_and_skips_unwatched():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            common = dict(
                user_id=user.scratch_id,
                genres=[],
                studios=[],
                countries=[],
                languages=[],
                tags=[],
                features=[],
                locked_fields=[],
            )
            db.add_all(
                [
                    Movie(
                        title="Seen twice",
                        sort_title="a",
                        status=MovieStatus.WATCHED,
                        runtime_minutes=100,
                        rewatches=1,
                        **common,
                    ),
                    Movie(
                        title="Planned",
                        sort_title="b",
                        status=MovieStatus.WISHLIST,
                        runtime_minutes=200,
                        **common,
                    ),
                ]
            )
            await db.flush()
            movie = (await get_media_stats(db, user))["movie"]
            assert movie["minutes_first"] == 100
            assert movie["minutes_rewatch"] == 100
            assert movie["minutes_watched"] == 200  # the planned movie adds nothing
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_a_notification_uses_the_exact_air_time_and_is_created_once():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user)
            db.add(show)
            await db.flush()
            season = AnimeSeason(show_id=show.id, season_number=1, episode_count=12)
            db.add(season)
            await db.flush()
            aired_at = int(datetime.now(tz=timezone.utc).timestamp()) - 3 * 3600
            db.add(AnimeEpisode(season_id=season.id, episode_number=5, air_at=aired_at))
            await db.flush()

            await generate_for_user(db, user.scratch_id)
            await generate_for_user(db, user.scratch_id)  # asking again must not notify twice
            rows = (
                (
                    await db.execute(
                        select(Notification).where(Notification.user_id == user.scratch_id)
                    )
                )
                .scalars()
                .all()
            )
            assert len(rows) == 1
            assert rows[0].kind == "episode_aired"
            assert rows[0].body == "Episode 5 aired"
            assert rows[0].event_at == aired_at
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_completed_and_dropped_titles_never_notify():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            now = int(datetime.now(tz=timezone.utc).timestamp())
            for status in (AnimeStatus.WATCHED, AnimeStatus.DROPPED):
                show = _anime(user, title=f"done {status.value}", status=status)
                db.add(show)
                await db.flush()
                season = AnimeSeason(show_id=show.id, season_number=1)
                db.add(season)
                await db.flush()
                db.add(AnimeEpisode(season_id=season.id, episode_number=3, air_at=now - 600))
            await db.flush()
            await generate_for_user(db, user.scratch_id)
            rows = (
                (
                    await db.execute(
                        select(Notification).where(Notification.user_id == user.scratch_id)
                    )
                )
                .scalars()
                .all()
            )
            assert rows == []
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_progress_counter_counts_as_watched_even_without_flagged_episode_rows():
    """Most history lives in the season progress counter (what the library
    list shows), not in per-episode flags, and it must count."""
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user, status=AnimeStatus.WATCHED, runtime=20)
            db.add(show)
            await db.flush()
            # 10 of 12 by counter, 8 rows on record, none flagged: 2 counted with no row
            season = AnimeSeason(
                show_id=show.id, season_number=1, episode_count=12, episodes_watched=10
            )
            db.add(season)
            await db.flush()
            db.add_all(
                [
                    AnimeEpisode(season_id=season.id, episode_number=n, runtime_minutes=25)
                    for n in range(1, 9)
                ]
            )
            await db.flush()

            anime = (await get_media_stats(db, user))["anime"]
            assert anime["episodes_watched"] == 10
            assert (
                anime["minutes_watched"] == 8 * 25 + 2 * 20
            )  # rows use their own runtime, the rest the show's
            assert anime["seasons_completed"] == 0  # 10 of 12 is not a finished season
            assert anime["seasons_in_progress"] == 1
            assert anime["most_watched"][0]["episodes"] == 10
        finally:
            if user is not None:
                await _cleanup(db, user)


@pytest.mark.asyncio
async def test_a_counter_covering_every_episode_completes_the_season():
    async with SessionLocal() as db:
        user = None
        try:
            user = await _user(db)
            show = _anime(user, status=AnimeStatus.WATCHED)
            db.add(show)
            await db.flush()
            db.add(
                AnimeSeason(show_id=show.id, season_number=1, episode_count=26, episodes_watched=26)
            )
            await db.flush()
            anime = (await get_media_stats(db, user))["anime"]
            assert anime["seasons_completed"] == 1
            assert anime["episodes_watched"] == 26
            assert anime["minutes_watched"] == 26 * 24  # no rows on record: the show's runtime
        finally:
            if user is not None:
                await _cleanup(db, user)
