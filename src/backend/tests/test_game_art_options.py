"""The cover and banner choices offered while adding a game."""

from types import SimpleNamespace

from src.api.routes import games as game_routes
from src.core.auth import get_current_user
from src.main import app
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_art_options_lists_what_steamgriddb_has(flow, monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=flow.user_id, steamgriddb_api_key="key"
    )
    seen = {}

    def fake(title, provider, provider_id, key):
        seen.update(title=title, provider=provider, provider_id=provider_id, key=key)
        return {"configured": True, "covers": ["https://a/1.png"], "banners": ["https://a/2.png"]}

    monkeypatch.setattr(game_routes, "find_art_options", fake)
    response = await flow.client.get(
        "/api/game/art-options", params={"title": "Hades", "provider": "Steam", "provider_id": "1145360"}
    )
    assert response.status_code == 200
    assert response.json()["covers"] == ["https://a/1.png"]
    assert seen == {"title": "Hades", "provider": "Steam", "provider_id": "1145360", "key": "key"}


async def test_without_a_key_it_says_so(flow, monkeypatch) -> None:
    from src.features.metadata.games import search

    monkeypatch.setattr(search.settings, "STEAMGRIDDB_API_KEY", None)
    assert search.find_art_options("Hades", "Steam", "1", None) == {
        "configured": False,
        "covers": [],
        "banners": [],
    }
