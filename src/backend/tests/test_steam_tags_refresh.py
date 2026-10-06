"""Refreshing the genres of existing Steam games from the tags players vote on."""

import pytest
from sqlalchemy import select

from src.database.models.game import Game
from src.database.session import SessionLocal
from src.features.metadata.games import steam, steam_tags
from tests.test_game_files_flow import game_flow  # noqa: F401  (registers the "flow" fixture)
from tests.test_steam_tags import ELDEN_RING


async def _game(flow, title: str, source: str | None, app_id: str | None, tags: list[str]) -> str:  # noqa: F811
    created = await flow.client.post(
        "/api/game/create",
        json={
            "title": title,
            "folder_location": title.replace(" ", "_"),
            "source": source,
            "tags": tags,
        },
    )
    assert created.status_code in (200, 201), created.text
    game_id = created.json()["id"]
    async with SessionLocal() as db:
        game = await db.get(Game, game_id)
        game.external_id = app_id
        await db.commit()
    return game_id


async def _tags(game_id: str) -> list[str]:
    async with SessionLocal() as db:
        return list((await db.scalar(select(Game.tags).where(Game.id == game_id))) or [])


@pytest.fixture
def steam_pages(monkeypatch):
    monkeypatch.setattr(
        steam_tags, "fetch_player_tags", lambda app_id: ELDEN_RING if app_id == 1245620 else []
    )
    monkeypatch.setattr(
        steam,
        "get_app_details",
        lambda app_id: {"genres": [{"description": "Action"}, {"description": "RPG"}]},
    )


async def test_steam_games_get_player_tags_and_keep_their_own(flow, steam_pages) -> None:
    elden = await _game(flow, "Elden Ring", "Steam", "1245620", ["Steam", "my favourite"])
    quiet = await _game(flow, "Quiet Game", "Steam", "99", ["Steam"])
    other = await _game(flow, "GOG Game", "GOG", "5", ["old"])

    response = await flow.client.post("/api/library-sync/steam-tags/refresh")
    assert response.status_code == 200, response.text
    body = response.json()
    assert (
        body["total"] == 2
        and body["processed"] == 2
        and body["updated"] == 1
        and body["done"] is True
    )

    tags = await _tags(elden)
    assert tags[:3] == ["Souls-like", "Open World", "Dark Fantasy"]
    assert "my favourite" in tags and "Steam" in tags
    assert "Multiplayer" not in tags
    # no player tags on the page: left as it was, and non-Steam games are not touched
    assert await _tags(quiet) == ["Steam"]
    assert await _tags(other) == ["old"]


async def test_the_refresh_is_done_a_few_games_at_a_time(flow, steam_pages) -> None:
    for i in range(3):
        await _game(flow, f"Steam Game {i}", "Steam", str(1245620 if i == 0 else 100 + i), [])
    first = (
        await flow.client.post("/api/library-sync/steam-tags/refresh", params={"limit": 2})
    ).json()
    assert (first["processed"], first["done"]) == (2, False)
    second = (
        await flow.client.post(
            "/api/library-sync/steam-tags/refresh", params={"limit": 2, "offset": 2}
        )
    ).json()
    assert (second["processed"], second["done"]) == (1, True)
