"""Media smart lists can ask for the year a title was finished or released,
for shows still airing, and for shows with aired episodes not watched yet."""

import time
import uuid
from datetime import date, timedelta
from types import SimpleNamespace

import pytest
from fastapi import Response
from sqlalchemy import delete

from src.api.routes import games
from src.api.routes.media_lists import _resolve_smart_items
from src.api.schemas.game import GameCreate
from src.database.models.movies import Movie, MovieStatus
from src.database.models.tv_show import TVEpisode, TVSeason, TVShow, TVShowStatus
from src.database.models.user import User
from src.database.session import SessionLocal


@pytest.fixture
async def library():
    now = int(time.time())
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        behind = TVShow(
            user_id=user.id,
            title="Behind Show",
            sort_title="behind show",
            status=TVShowStatus.IN_PROGRESS,
            is_airing=True,
            first_air_date=date(2020, 1, 1),
        )
        caught_up = TVShow(
            user_id=user.id,
            title="Caught Up Show",
            sort_title="caught up show",
            status=TVShowStatus.IN_PROGRESS,
            is_airing=False,
            first_air_date=date(1998, 1, 1),
        )
        movie = Movie(
            user_id=user.id,
            title="Finished Film",
            sort_title="finished film",
            status=MovieStatus.WATCHED,
            end_date=date(2026, 2, 3),
            release_date=date(1994, 6, 1),
        )
        db.add_all([behind, caught_up, movie])
        await db.flush()
        for show, episodes in (
            # one aired and unwatched, one not aired yet
            (behind, [(1, True, now - 86400), (2, False, now - 3600), (3, False, now + 86400)]),
            # everything aired is watched; the next one has not aired
            (caught_up, [(1, True, now - 86400), (2, False, now + 86400)]),
        ):
            season = TVSeason(show_id=show.id, season_number=1)
            db.add(season)
            await db.flush()
            for number, watched, air_at in episodes:
                db.add(
                    TVEpisode(
                        season_id=season.id,
                        episode_number=number,
                        watched=watched,
                        air_at=air_at,
                        air_date=date.today() - timedelta(days=1) if air_at < now else None,
                    )
                )
        await db.commit()
        user_id = user.id
    yield user_id
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _titles(user_id, rule) -> list[str]:
    async with SessionLocal() as db:
        return [i["title"] for i in await _resolve_smart_items(rule, user_id, db, "english")]


async def test_episodes_behind_and_airing(library) -> None:
    assert await _titles(library, {"episodes_behind": True}) == ["Behind Show"]
    assert await _titles(library, {"airing": True}) == ["Behind Show"]


async def test_finished_and_released_years(library) -> None:
    assert await _titles(library, {"finished_year": 2026}) == ["Finished Film"]
    assert await _titles(library, {"finished_year": 2025}) == []
    assert await _titles(library, {"released_from": 1990, "released_to": 1999}) == [
        "Caught Up Show",
        "Finished Film",
    ]
    assert await _titles(library, {"added_within_days": 1}) == [
        "Behind Show",
        "Caught Up Show",
        "Finished Film",
    ]


async def test_a_list_with_no_type_picked_never_takes_games(library) -> None:
    async with SessionLocal() as db:
        await games.create_game(
            GameCreate(title="A Game", folder_location="A_Game"),
            Response(),
            db,
            SimpleNamespace(id=library),
        )
    assert "A Game" not in await _titles(library, {"added_within_days": 1})
