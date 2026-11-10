"""A newly added show opens with every season TVmaze lists, not only Season 1
until the page is reloaded, and a slow TVmaze never holds the page up for long."""

import asyncio
import time
import uuid

import httpx
import pytest
from sqlalchemy import delete

from src.api.routes import tv_shows
from src.core.auth import get_current_user
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow, TVShowStatus
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import tv_seasons
from src.main import app

_LISTED = [
    {"season_number": n, "name": None, "episode_count": 10, "air_date": f"201{n}-01-01"}
    for n in range(1, 4)
]


class _FakeTVMaze:
    delay = 0.0

    def seasons(self, _id):
        time.sleep(self.delay)
        return _LISTED


class _SlowTVMaze(_FakeTVMaze):
    delay = 2.0


@pytest.fixture
async def new_show():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        show = TVShow(
            user_id=user.id,
            title="First Open",
            sort_title="first open",
            status=TVShowStatus.WISHLIST,
            external_id="1",
            creators=[],
            studios=[],
            countries=[],
            languages=[],
            genres=[],
            tags=[],
            features=[],
            locked_fields=[],
        )
        db.add(show)
        await db.flush()
        # what Add Show saves when the search had no season list, with the
        # episodes the airing check fills in
        season = TVSeason(show_id=show.id, season_number=1)
        db.add(season)
        await db.flush()
        db.add(TVEpisode(season_id=season.id, episode_number=1, title="Pilot"))
        await db.commit()
        user_id, show_id = user.id, show.id
    app.dependency_overrides[get_current_user] = lambda: User(id=user_id)
    yield show_id
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _open(show_id) -> dict:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/tv/get/{show_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def test_the_first_open_lists_every_season(new_show, monkeypatch) -> None:
    monkeypatch.setattr(tv_seasons, "TVMazeClient", _FakeTVMaze)
    show = await _open(new_show)
    assert sorted(s["season_number"] for s in show["seasons"]) == [1, 2, 3]
    [first] = [s for s in show["seasons"] if s["season_number"] == 1]
    assert [e["title"] for e in first["episodes"]] == ["Pilot"]


async def test_a_slow_tvmaze_does_not_hold_the_page(new_show, monkeypatch) -> None:
    monkeypatch.setattr(tv_seasons, "TVMazeClient", _SlowTVMaze)
    monkeypatch.setattr(tv_shows, "_FIRST_CHECK_WAIT_SECONDS", 0.2)
    started = time.monotonic()
    show = await _open(new_show)
    assert time.monotonic() - started < 1.5
    assert [s["season_number"] for s in show["seasons"]] == [1]
    # the check still finishes on its own, so the next open has them
    deadline = time.monotonic() + 5
    while new_show in tv_seasons._inflight and time.monotonic() < deadline:
        await asyncio.sleep(0.1)
    monkeypatch.setattr(tv_seasons, "TVMazeClient", _FakeTVMaze)
    show = await _open(new_show)
    assert sorted(s["season_number"] for s in show["seasons"]) == [1, 2, 3]


async def test_adding_a_show_that_is_still_airing_works(new_show, monkeypatch) -> None:
    """The airing check at creation saves the season's episodes, which used to
    fail because the new season had no id yet, so no airing show could be added."""
    from src.features.metadata import refresh

    async def airing(_id):
        return True, []

    async def next_episode(_id):
        return None, None, []

    async def episodes(_id, season_number):
        return [
            {"episode_number": n, "title": f"Episode title {n}", "air_date": "2022-02-18"}
            for n in (1, 2)
        ], []

    monkeypatch.setattr(refresh, "fetch_is_airing", airing)
    monkeypatch.setattr(refresh, "fetch_next_episode", next_episode)
    monkeypatch.setattr(refresh, "fetch_season_episodes", episodes)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/tv/create",
            json={
                "title": "Still Airing",
                "external_id": "2",
                "seasons": [{"season_number": 1, "episode_count": 2}],
            },
        )
    assert response.status_code == 201, response.text
    [season] = response.json()["seasons"]
    assert [e["title"] for e in season["episodes"]] == ["Episode title 1", "Episode title 2"]
