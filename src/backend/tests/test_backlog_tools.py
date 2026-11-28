"""Set aside keeps everything a game has, and the Library tab of films,
shows and anime holds the groups chosen in Settings."""

from src.core.preferences import save_preferences
from src.database.models.movies import Movie, MovieStatus
from src.database.session import SessionLocal
from tests.test_game_files_flow import flow  # noqa: F401  (the fixture)


async def test_set_aside_records_when_and_bringing_back_clears_it(flow) -> None:  # noqa: F811
    response = await flow.client.patch(
        f"/api/game/update/{flow.game_id}",
        json={"set_aside": True, "set_aside_reason": "online_only"},
    )
    assert response.status_code == 200, response.text
    game = response.json()
    assert game["set_aside_at"] and game["set_aside_reason"] == "online_only"
    first = game["set_aside_at"]

    # setting it aside again keeps the day it was first set aside
    again = (
        await flow.client.patch(f"/api/game/update/{flow.game_id}", json={"set_aside": True})
    ).json()
    assert again["set_aside_at"] == first

    back = (
        await flow.client.patch(f"/api/game/update/{flow.game_id}", json={"set_aside": False})
    ).json()
    assert back["set_aside_at"] is None and back["set_aside_reason"] is None
    # everything else stays as it was
    assert back["title"] == "Flow"


async def test_bulk_set_aside(flow) -> None:  # noqa: F811
    response = await flow.client.patch(
        "/api/game/bulk-update",
        json={"game_ids": [str(flow.game_id)], "set_aside": True},
    )
    assert response.status_code == 200, response.text
    game = (await flow.client.get(f"/api/game/get/{flow.game_id}")).json()
    assert game["set_aside_at"]
    # an unknown reason is refused
    bad = await flow.client.patch(
        f"/api/game/update/{flow.game_id}",
        json={"set_aside": True, "set_aside_reason": "bored"},
    )
    assert bad.status_code == 422


async def test_the_media_library_tab_follows_the_setting(flow) -> None:  # noqa: F811
    async with SessionLocal() as db:
        for title, status in (
            ("Watched", MovieStatus.WATCHED),
            ("Dropped", MovieStatus.DROPPED),
            ("Planned", MovieStatus.WATCHLIST),
        ):
            db.add(
                Movie(user_id=flow.user_id, title=title, sort_title=title.lower(), status=status)
            )
        await db.commit()

    async def library() -> list[str]:
        r = await flow.client.get("/api/movie/list", params={"status_bucket": "library"})
        assert r.status_code == 200, r.text
        return sorted(m["title"] for m in r.json()["items"])

    # by default everything but Plan to Watch
    assert await library() == ["Dropped", "Watched"]
    async with SessionLocal() as db:
        await save_preferences(db, flow.user_id, {"library_statuses_media": ["completed"]})
    assert await library() == ["Watched"]
    # nothing ticked shows nothing, not everything
    async with SessionLocal() as db:
        await save_preferences(db, flow.user_id, {"library_statuses_media": []})
    assert await library() == []
