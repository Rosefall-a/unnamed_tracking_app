"""The Library tab: every title you have started or finished, so everything
except Plan to Watch (both codes it is stored under)."""

import uuid

import httpx
import pytest
from sqlalchemy import delete

from src.core.auth import get_current_user
from src.database.models.anime import Anime, AnimeStatus
from src.database.models.user import User
from src.database.session import SessionLocal
from src.main import app


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
        for title, status in (
            ("Planned", AnimeStatus.WISHLIST),
            ("Planned too", AnimeStatus.WATCHLIST),
            ("Watching", AnimeStatus.IN_PROGRESS),
            ("Finished", AnimeStatus.WATCHED),
            ("On hold", AnimeStatus.BACKLOG),
            ("Dropped", AnimeStatus.DROPPED),
        ):
            db.add(
                Anime(
                    user_id=user.id,
                    title=title,
                    sort_title=title.lower(),
                    status=status,
                    studios=[],
                    countries=[],
                    languages=[],
                    genres=[],
                    tags=[],
                    features=[],
                    locked_fields=[],
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


async def _titles(bucket: str) -> list[str]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/anime/list", params={"status_bucket": bucket})
    assert response.status_code == 200, response.text
    return sorted(item["title"] for item in response.json()["items"])


async def test_the_library_tab_leaves_out_only_plan_to_watch(person) -> None:
    assert await _titles("library") == ["Dropped", "Finished", "On hold", "Watching"]
    assert await _titles("plan") == ["Planned", "Planned too"]
