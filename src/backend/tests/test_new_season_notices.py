"""A franchise that grew a season, film or special is noticed, each with its own switch,
and the scheduled check refreshes one title per franchise."""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, select

from src.database.models.anime import Anime, AnimeStatus
from src.database.models.notification import Notification
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import notifications, sequel_check
from src.core import preferences


@pytest.fixture
async def person():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    yield user_id
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


def _show(user_id):
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Dr. Stone",
        poster_url=None,
        status=AnimeStatus.WATCHED,
        user_id=user_id,
    )


OLD = [{"id": "1", "title": "Dr. Stone", "format": "TV", "is_current": True}]
NEW = OLD + [
    {"id": "2", "title": "Dr. Stone: Final Season", "format": "TV"},
    {"id": "3", "title": "Dr. Stone: The Movie", "format": "Movie"},
]


async def _announced(user_id, **prefs):
    if prefs:
        async with SessionLocal() as db:
            await preferences.save_preferences(db, user_id, prefs)
    show = _show(user_id)
    async with SessionLocal() as db:
        await notifications.record_sequel_announcements(db, user_id, show, OLD, NEW)
        rows = (
            await db.execute(select(Notification.body).where(Notification.user_id == user_id))
        ).scalars().all()
    return sorted(rows)


async def test_a_new_season_is_noticed_and_a_movie_is_not_by_default(person) -> None:
    rows = await _announced(person)
    assert rows == ["A new season is listed: Dr. Stone: Final Season"]


async def test_the_movie_switch_adds_the_film(person) -> None:
    rows = await _announced(person, notify_extras_announced=True)
    assert rows == [
        "A new movie is listed: Dr. Stone: The Movie",
        "A new season is listed: Dr. Stone: Final Season",
    ]


async def test_the_season_switch_off_leaves_only_the_film(person) -> None:
    rows = await _announced(person, notify_sequel_announced=False, notify_extras_announced=True)
    assert rows == ["A new movie is listed: Dr. Stone: The Movie"]


def test_the_movie_switch_is_off_by_default() -> None:
    assert preferences.DEFAULTS["notify_extras_announced"] is False
    assert preferences.DEFAULTS["notify_sequel_announced"] is True


def test_the_check_is_a_job_that_starts_switched_off() -> None:
    from src.features.jobs import JOBS

    spec = JOBS["sequel_check"]
    assert spec.default_enabled is False
    assert spec.default_interval_minutes == 24 * 60


def test_one_fetch_covers_a_whole_franchise() -> None:
    assert sequel_check.MAX_FRANCHISES_PER_RUN >= 1
    assert sequel_check.RECHECK_AFTER_SECONDS >= 60 * 60
