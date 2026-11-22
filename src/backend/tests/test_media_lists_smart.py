"""What Home asks for on every visit stays quick: the Favorites list fills
itself from the favorite flag reading only the titles, and a library page reads
each season's counts but never its episodes."""

import uuid

import httpx
import pytest
from sqlalchemy import delete, event

from src.core.auth import get_current_user
from src.database.models.anime import Anime, AnimeSeason, AnimeStatus
from src.database.models.user import User
from src.database.session import SessionLocal, engine
from src.main import app


def _anime(user_id, title: str, favorite: bool, deleted: bool = False) -> Anime:
    return Anime(
        user_id=user_id,
        title=title,
        sort_title=title.lower(),
        status=AnimeStatus.WATCHED,
        favorite=favorite,
        deleted_at=1 if deleted else None,
        studios=[],
        countries=[],
        languages=[],
        genres=[],
        tags=[],
        features=[],
        locked_fields=[],
    )


@pytest.fixture
async def person():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        loved = _anime(user.id, "Loved", True)
        db.add_all(
            [
                loved,
                _anime(user.id, "Also loved", True),
                _anime(user.id, "Just watched", False),
                _anime(user.id, "Loved then deleted", True, deleted=True),
            ]
        )
        await db.flush()
        db.add(AnimeSeason(show_id=loved.id, season_number=1, episodes_watched=0))
        await db.commit()
        user_id = user.id
    app.dependency_overrides[get_current_user] = lambda: User(id=user_id)
    yield user_id
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def _get(path: str) -> tuple[httpx.Response, list[str]]:
    """The response, and every SQL statement the request ran."""
    statements: list[str] = []

    def note(_conn, _cursor, statement, *_args) -> None:
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", note)
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(path)
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", note)
    assert response.status_code == 200, response.text
    return response, statements


async def test_favorites_lists_only_favorites_and_never_loads_seasons(person) -> None:
    response, statements = await _get("/api/lists")
    favorites = next(lst for lst in response.json() if lst["name"] == "Favorites")
    assert favorites["item_count"] == 2
    assert favorites["type_counts"] == {"movie": 0, "tv": 0, "anime": 2}
    assert not [s for s in statements if "FROM anime_seasons" in s]


async def test_a_library_page_sends_seasons_without_loading_episodes(person) -> None:
    response, statements = await _get("/api/anime/list")
    loved = next(i for i in response.json()["items"] if i["title"] == "Loved")
    assert [s["season_number"] for s in loved["seasons"]] == [1]
    assert not [s for s in statements if "FROM anime_episodes" in s]
