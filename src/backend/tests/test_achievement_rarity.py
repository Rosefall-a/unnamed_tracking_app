"""Steam rarity is filled in for achievements that have none, without ever
clearing one Steam did not answer for, and a refresh where Steam says nothing
keeps the rarity already saved."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import Response
from sqlalchemy import delete, select

from src.api.routes import games, library_sync
from src.database.models.achievement import Achievement
from src.database.models.game import Game
from src.database.models.user import User
from src.database.session import SessionLocal
from src.features import achievement_rarity
from src.api.schemas.game import GameCreate

_SCHEMA = {
    "ACH_A": {"displayName": "A", "description": "a", "icon": "", "icongray": "", "hidden": 0},
    "ACH_B": {"displayName": "B", "description": "b", "icon": "", "icongray": "", "hidden": 0},
}


@pytest.fixture
async def steam_game():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id
    who = SimpleNamespace(id=user_id, steam_id="76561190000000000", steam_api_key="key")
    async with SessionLocal() as db:
        game = await games.create_game(
            GameCreate(title="Rarity Test", folder_location="Rarity_Test"), Response(), db, who
        )
        row = await db.get(Game, game.id)
        row.source, row.external_id = "Steam", "12345"
        for name, percent in (("ACH_A", None), ("ACH_B", 42.0)):
            db.add(
                Achievement(
                    game_id=game.id,
                    provider="Steam",
                    external_id=name,
                    name=name,
                    unlocked=False,
                    global_percent=percent,
                    created_at=1,
                )
            )
        await db.commit()
        game_id = game.id
    yield who, game_id
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _percents(game_id) -> dict[str, float | None]:
    async with SessionLocal() as db:
        rows = (await db.execute(select(Achievement).where(Achievement.game_id == game_id))).scalars()
        return {a.external_id: a.global_percent for a in rows}


async def test_repair_fills_only_what_steam_gives_and_keeps_the_rest(steam_game, monkeypatch):
    who, game_id = steam_game
    assert await achievement_rarity.count_missing_rarity(who.id) == 1
    monkeypatch.setattr(achievement_rarity.steam, "get_global_percentages", lambda _app: {"ACH_A": 3.5})
    seen: list[tuple[int, int]] = []
    result = await achievement_rarity.fill_missing_rarity(who.id, lambda d, t: seen.append((d, t)))
    assert result == {"rarity": 1, "no_rarity": 0}
    assert await _percents(game_id) == {"ACH_A": 3.5, "ACH_B": 42.0}
    assert seen[-1] == (1, 1)
    assert await achievement_rarity.count_missing_rarity(who.id) == 0


async def test_steam_saying_nothing_changes_nothing(steam_game, monkeypatch):
    who, game_id = steam_game
    monkeypatch.setattr(achievement_rarity.steam, "get_global_percentages", lambda _app: {})
    result = await achievement_rarity.fill_missing_rarity(who.id, lambda d, t: None)
    assert result == {"rarity": 0, "no_rarity": 1}
    assert await _percents(game_id) == {"ACH_A": None, "ACH_B": 42.0}


async def test_a_refresh_with_no_rarity_answer_keeps_the_saved_one(steam_game, monkeypatch):
    who, game_id = steam_game
    monkeypatch.setattr(library_sync.steam, "resolve_steam_id", lambda sid, _key: sid)
    monkeypatch.setattr(library_sync.steam, "get_schema_for_game", lambda _key, _app: _SCHEMA)
    monkeypatch.setattr(
        library_sync.steam,
        "get_player_achievements",
        lambda *_args: [{"apiname": "ACH_A", "achieved": 1, "unlocktime": 1_700_000_000}],
    )
    monkeypatch.setattr(library_sync.steam, "get_global_percentages", lambda _app: {})
    async with SessionLocal() as db:
        await library_sync.refresh_game_achievements(game_id, db, who)
    assert (await _percents(game_id))["ACH_B"] == 42.0
