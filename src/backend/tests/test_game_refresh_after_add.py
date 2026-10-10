"""A game added from the quick add is filled in by a refresh that checks the game
was not changed in between (the `expected_updated_at` path)."""

from types import SimpleNamespace

from sqlalchemy import delete

from src.api.routes import games as game_routes
from src.core.auth import get_current_user
from src.database.models.game import GameLink
from src.database.session import SessionLocal
from src.main import app
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_the_refresh_after_adding_fills_the_game_in(flow, monkeypatch) -> None:
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=flow.user_id, steamgriddb_api_key=None
    )
    monkeypatch.setattr(
        game_routes,
        "search_game_metadata",
        lambda *_a, **_k: {
            "providers": ["IGDB"],
            "provider_errors": [],
            "results": [
                {
                    "provider": "IGDB",
                    "title": "Flow",
                    "description": "A cat on a flood.",
                    "developer": "Dev",
                    "release_date": "2024-01-01",
                    "links": [{"label": "IGDB", "url": "https://igdb.test/flow"}],
                }
            ],
        },
    )
    game = (await flow.client.get(f"/api/game/list")).json()[0]

    response = await flow.client.post(
        f"{flow.game}/metadata/refresh",
        json={
            "dry_run": False,
            "update_text": True,
            "fill_missing_art": False,
            "overwrite_existing_art": False,
            "expected_updated_at": game["updated_at"],
        },
    )

    assert response.status_code == 200, response.text
    after = (await flow.client.get("/api/game/list")).json()[0]
    assert after["description"] == "A cat on a flood."
    assert after["developer"] == "Dev"
    assert [link["url"] for link in after["links"]] == ["https://igdb.test/flow"]

    # the fixture's cleanup removes the game, which its links still point at
    async with SessionLocal() as db:
        await db.execute(delete(GameLink).where(GameLink.game_id == flow.game_id))
        await db.commit()
