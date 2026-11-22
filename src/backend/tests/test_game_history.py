"""A game's history in the History tab: the days it was played, finished and
bought, and the achievements unlocked each day with their names, as far back
as the data goes, whatever the calendar is set to show."""

import uuid
from datetime import datetime

import httpx
import pytest
from sqlalchemy import delete

from src.core import preferences
from src.core.auth import get_current_user
from src.database.models.achievement import Achievement
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import SessionLocal
from src.main import app


def _stamp(day: str, hour: int = 12) -> int:
    return int(datetime.fromisoformat(f"{day}T{hour:02d}:00:00+00:00").timestamp())


@pytest.fixture
async def player():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        game = Game(
            user_id=user.id,
            title="Celeste",
            sort_title="celeste",
            folder_location=f"Celeste-{uuid.uuid4().hex[:6]}",
            status=GameStatus.MASTERED,
            last_played_at=_stamp("2024-03-02"),
            completion_date=_stamp("2019-06-01"),
            purchase_date=_stamp("2018-01-25"),
        )
        db.add(game)
        await db.flush()
        for i, (name, day, hour) in enumerate(
            (
                ("Forsaken City", "2018-02-01", 10),
                ("Old Site", "2018-02-01", 11),
                ("Celestial Resort", "2018-02-01", 12),
                ("Golden Ridge", "2018-02-01", 13),
                ("Summit", "2019-06-01", 9),
            )
        ):
            db.add(
                Achievement(
                    game_id=game.id,
                    provider="Steam",
                    external_id=f"a{i}",
                    name=name,
                    unlocked=True,
                    unlocked_at=_stamp(day, hour),
                    created_at=_stamp("2018-01-25"),
                )
            )
        db.add(
            Achievement(
                game_id=game.id,
                provider="Steam",
                external_id="locked",
                name="Farewell",
                unlocked=False,
                created_at=_stamp("2018-01-25"),
            )
        )
        await db.commit()
        user_id = user.id
    app.dependency_overrides[get_current_user] = lambda: User(id=user_id)
    yield user_id
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _get(path: str) -> list[dict]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(path)
    assert response.status_code == 200, response.text
    return response.json()


async def test_history_goes_back_as_far_as_the_data(player) -> None:
    entries = await _get("/api/history/games")
    by_kind = {(e["kind"], e["date"]): e for e in entries}
    assert set(by_kind) == {
        ("game_purchased", "2018-01-25"),
        ("game_achievements", "2018-02-01"),
        ("game_achievements", "2019-06-01"),
        ("game_finished", "2019-06-01"),
        ("game_played", "2024-03-02"),
    }
    first_day = by_kind[("game_achievements", "2018-02-01")]
    # every unlock is counted; the first three are named, in the order they came
    assert first_day["count"] == 4
    assert first_day["names"] == ["Forsaken City", "Old Site", "Celestial Resort"]
    assert by_kind[("game_achievements", "2019-06-01")]["names"] == ["Summit"]
    # oldest first, and a locked achievement is never in it
    assert [e["date"] for e in entries] == sorted(e["date"] for e in entries)


async def test_hiding_games_on_the_calendar_keeps_the_history(player) -> None:
    async with SessionLocal() as db:
        await preferences.save_preferences(db, player, {"calendar_hide_games": True})
    assert await _get("/api/calendar/games") == []
    assert len(await _get("/api/history/games")) == 5


async def test_the_calendar_still_shows_game_history_when_switched_on(player) -> None:
    kinds = {e["kind"] for e in await _get("/api/calendar/games")}
    assert {"game_played", "game_finished", "game_purchased", "game_achievements"} <= kinds
