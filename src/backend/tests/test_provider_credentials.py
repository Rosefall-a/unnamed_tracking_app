"""What Settings shows about each connected library."""

import time
import uuid

import httpx
import pytest
from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_user
from src.database.models.game import Game, GameStatus
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.main import app


@pytest.fixture
async def client():
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.flush()
        for n, source in enumerate(["Steam", "Steam", "Steam", "Epic Games", None]):
            db.add(
                Game(
                    user_id=user.id,
                    title=f"Game {n}",
                    sort_title=f"game {n}",
                    folder_location=f"Game-{n}",
                    source=source,
                    status=GameStatus.BACKLOG,
                    # the third Steam game is in the trash
                    deleted_at=int(time.time()) if n == 2 else None,
                )
            )
        await db.commit()
        user_id = user.id

    async def current_user(db: AsyncSession = Depends(get_db)) -> User:
        found = await db.get(User, user_id)
        assert found is not None
        return found

    app.dependency_overrides[get_current_user] = current_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_library_counts_leave_out_the_trash(client) -> None:
    reply = await client.get("/api/settings/provider-credentials")
    assert reply.status_code == 200, reply.text
    counts = {k: v.get("library_games") for k, v in reply.json().items() if "library_games" in v}
    assert counts == {"Steam": 2, "Epic Games": 1, "RetroAchievements": 0, "PlayStation": 0}
