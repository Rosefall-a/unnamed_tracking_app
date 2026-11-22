"""Page choices (Pick again, view modes, collection order) live on the server:
saved with when they changed, kept apart per person, and moved over from an
older browser without overwriting anything already saved."""

import uuid

import httpx
import pytest
from sqlalchemy import delete, select

from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.models.user_ui_state import UserUiState
from src.database.session import SessionLocal
from src.main import app


async def _make_user() -> uuid.UUID:
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        return user.id


@pytest.fixture
async def people():
    ids = [await _make_user(), await _make_user()]
    yield ids
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()


def _as(user_id) -> httpx.AsyncClient:
    app.dependency_overrides[get_current_user] = lambda: User(id=user_id)
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


async def test_a_pick_is_saved_with_its_time_and_only_for_its_owner(people) -> None:
    me, other = people
    async with _as(me) as client:
        pick = {"day": "2026-11-10", "key": "anime:1"}
        assert (await client.put("/api/ui-state/homePick:w1", json={"value": pick})).status_code == 204
        assert (await client.get("/api/ui-state")).json() == {"homePick:w1": pick}
    async with SessionLocal() as db:
        row = await db.scalar(select(UserUiState).where(UserUiState.user_id == me))
        assert row is not None and row.updated_at > 0
    async with _as(other) as client:
        assert (await client.get("/api/ui-state")).json() == {}
    async with _as(me) as client:
        assert (await client.delete("/api/ui-state/homePick:w1")).status_code == 204
        assert (await client.get("/api/ui-state")).json() == {}


async def test_moving_browser_copies_never_overwrites_what_is_saved(people) -> None:
    me, _ = people
    async with _as(me) as client:
        await client.put("/api/ui-state/sidebarMode", json={"value": "pinned"})
        response = await client.post(
            "/api/ui-state/import",
            json={"values": {"sidebarMode": "rail", "manualCollections": ["Cozy"], "bad name!": 1}},
        )
        assert response.json() == {
            "stored": ["sidebarMode", "manualCollections"],
            "rejected": ["bad name!"],
        }
        assert (await client.get("/api/ui-state")).json() == {
            "sidebarMode": "pinned",
            "manualCollections": ["Cozy"],
        }


async def test_names_and_sizes_are_checked(people) -> None:
    me, _ = people
    async with _as(me) as client:
        assert (await client.put("/api/ui-state/bad name", json={"value": 1})).status_code == 422
        huge = "x" * (512 * 1024 + 1)
        assert (await client.put("/api/ui-state/big", json={"value": huge})).status_code == 413
