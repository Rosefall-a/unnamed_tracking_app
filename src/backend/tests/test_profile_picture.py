"""The profile picture's version: what lets the app skip asking for a picture
that doesn't exist, and lets a browser keep one until it changes."""

import io
import uuid

import httpx
import pytest
from fastapi import Depends
from PIL import Image
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes import users
from src.core.auth import get_current_user
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.main import app


def _png() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (32, 32), (200, 120, 40)).save(buffer, "PNG")
    return buffer.getvalue()


@pytest.fixture
async def client(tmp_path, monkeypatch):
    monkeypatch.setattr(users, "_USER_DATA_ROOT", tmp_path)
    async with SessionLocal() as db:
        user = User(
            username=f"t_{uuid.uuid4().hex[:10]}",
            email=f"{uuid.uuid4().hex[:10]}@example.test",
            password_hash="x",
        )
        db.add(user)
        await db.commit()
        user_id = user.id

    async def current_user(db: AsyncSession = Depends(get_db)) -> User:
        found = await db.get(User, user_id)
        assert found is not None
        return found

    app.dependency_overrides[get_current_user] = current_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        yield http, user_id
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


async def test_no_picture_means_no_version(client) -> None:
    http, _ = client
    me = (await http.get("/api/auth/me")).json()
    assert me["profile_picture_version"] is None


async def test_an_upload_gives_a_version_and_a_cacheable_address(client) -> None:
    http, user_id = client
    url = f"/api/user/{user_id}/profile-picture"
    upload = await http.put(url, files={"file": ("me.png", _png(), "image/png")})
    assert upload.status_code == 200, upload.text
    version = (await http.get("/api/auth/me")).json()["profile_picture_version"]
    assert isinstance(version, int) and str(version) == upload.json()["version"]

    versioned = await http.get(url, params={"v": version})
    assert versioned.status_code == 200
    assert "immutable" in versioned.headers["cache-control"]
    plain = await http.get(url)
    assert plain.headers["cache-control"].startswith("no-store")


async def test_a_missing_picture_is_still_a_404(client) -> None:
    http, user_id = client
    reply = await http.get(f"/api/user/{user_id}/profile-picture")
    assert reply.status_code == 404
