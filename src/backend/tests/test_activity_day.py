"""The activity grid's day list: what was watched and unlocked on one day."""

import time
import uuid
from datetime import date, datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import delete

from src.api.routes import media_stats
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.media_extras import ActivityEventType, ActivityLog, MediaType
from src.database.models.user import User
from src.database.session import SessionLocal

DAY = date(2026, 3, 14)


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
    yield SimpleNamespace(id=user_id)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_a_day_lists_episodes_and_achievements_with_links(person) -> None:
    show_id = uuid.uuid4()
    noon = int(datetime.combine(DAY, datetime.min.time()).timestamp()) + 12 * 3600
    async with SessionLocal() as db:
        db.add(
            ActivityLog(
                user_id=person.id,
                media_type=MediaType.TV,
                media_id=show_id,
                media_title="Severance",
                event_type=ActivityEventType.EPISODES_WATCHED,
                event_date=DAY,
                count=3,
            )
        )
        game = Game(user_id=person.id, title="Hades", sort_title="hades", folder_location=f"h_{uuid.uuid4().hex[:6]}")
        db.add(game)
        await db.flush()
        for name, ts in (("Escaped", noon), ("Other day", noon + 3 * 86_400)):
            db.add(
                Achievement(
                    game_id=game.id,
                    provider="Steam",
                    external_id=name,
                    name=name,
                    unlocked=True,
                    unlocked_at=ts,
                )
            )
        await db.commit()
        game_id = str(game.id)
        result = await media_stats.activity_for_day(DAY, db, person)

    assert result["episodes"] == [
        {"kind": "tv", "id": str(show_id), "title": "Severance", "count": 3, "detail": None}
    ]
    assert result["games"] == [
        {"kind": "game", "id": game_id, "title": "Hades", "achievements": ["Escaped"]}
    ]


async def test_a_quiet_day_is_empty(person) -> None:
    async with SessionLocal() as db:
        result = await media_stats.activity_for_day(date(2020, 1, 1), db, person)
    assert result == {"date": "2020-01-01", "episodes": [], "games": []}
