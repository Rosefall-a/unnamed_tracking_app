"""What the game form sends when it saves, through the real create and update routes."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import Response
from sqlalchemy import delete, select

from src.api.routes import games
from src.api.schemas.game import GameCreate, GameUpdate
from src.database.models.game import Game, GameLink
from src.database.models.user import User
from src.database.session import SessionLocal


@pytest.fixture(autouse=True)
def no_game_folders(monkeypatch):
    monkeypatch.setattr(games, "create_game_folder", lambda *_args: None)
    monkeypatch.setattr(games, "rename_game_folder", lambda *_args, **_kw: None, raising=False)


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
        # links are removed with their game first: the user delete does not cascade through them
        ids = select(Game.id).where(Game.user_id == user_id)
        await db.execute(delete(GameLink).where(GameLink.game_id.in_(ids)))
        await db.execute(delete(Game).where(Game.user_id == user_id))
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


# the fields the form sends on an edit, as the browser sends them (see services/games.ts)
FORM_BODY = {
    "title": "Form Game",
    "status": "BACKLOG",
    "favorite": True,
    "profiles_enabled": False,
    "osrs_stats_enabled": False,
    "page_settings": {},
    "description": "A description.",
    "developer": "Dev",
    "publisher": "Pub",
    "series": None,
    "parent_game_id": None,
    "relationship_type": None,
    "release_date": "2022-03-24",
    "source": "Steam",
    "region": None,
    "language": None,
    "age_rating": None,
    "time_to_beat_hours": 60.1,
    "time_to_beat_extras_hours": 101.4,
    "time_to_beat_completionist_hours": 136.2,
    "time_to_beat_all_hours": 105.6,
    "resume_note": "Level 3 next.",
    "rating_overall": 9.5,
    "rating_story": None,
    "rating_gameplay": None,
    "rating_soundtrack": None,
    "tags": ["Open World"],
    "features": ["Single-player"],
    "links": [{"label": "IGDB", "url": "https://www.igdb.com/games/119308"}],
    "collections": ["Backlog 2026"],
    "purchase_date": None,
    "completion_date": None,
    "purchase_price": None,
    "purchase_price_currency_code": None,
    "physical_condition": None,
    "folder_location": "Form-Game",
    "sort_title": None,
    "platform": "PC",
    "priority": None,
}


async def test_the_form_body_creates_and_then_updates_a_game(person) -> None:
    async with SessionLocal() as db:
        created = await games.create_game(
            GameCreate(title="Form Game", folder_location="Form-Game"), Response(), db, person
        )
        game_id = created.id

    async with SessionLocal() as db:
        updated = await games.update_game(game_id, GameUpdate.model_validate(FORM_BODY), db, person)

    assert float(updated.time_to_beat_hours) == 60.1
    assert float(updated.time_to_beat_extras_hours) == 101.4
    assert float(updated.time_to_beat_completionist_hours) == 136.2
    assert float(updated.time_to_beat_all_hours) == 105.6
    assert updated.resume_note == "Level 3 next."
    assert updated.collections == ["Backlog 2026"]
    assert updated.favorite is True
