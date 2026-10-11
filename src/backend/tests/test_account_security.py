"""Sign-in and account safety, through the real routes and real sessions."""

import secrets
import time
import uuid

import httpx
import pytest
from sqlalchemy import delete, text

from src.core.auth import hash_password, hash_token, session_cookie_name
from src.database.models.auth import UserApiKey, UserSession
from src.database.models.user import User
from src.database.session import SessionLocal
from src.main import app

PASSWORD = "Correct!9a"


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.fixture
async def made():
    """Users made by a test, removed again afterwards with what hangs off them."""
    ids: list[uuid.UUID] = []

    async def make(username: str, email: str | None = None, password: str = PASSWORD) -> User:
        async with SessionLocal() as db:
            user = User(
                username=username,
                email=email or f"{uuid.uuid4().hex[:10]}@example.test",
                password_hash=hash_password(password),
                is_active=True,
            )
            db.add(user)
            await db.commit()
            ids.append(user.id)
            return user

    yield make
    async with SessionLocal() as db:
        await db.execute(delete(UserSession).where(UserSession.user_id.in_(ids)))
        await db.execute(delete(UserApiKey).where(UserApiKey.user_id.in_(ids)))
        await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()


async def _database_wants_last_seen() -> bool:
    """A database used on another branch can carry a required `user_sessions.last_seen_at`
    that this code never sets, so the app's own sign-in cannot insert a session there."""
    async with SessionLocal() as db:
        row = await db.scalar(
            text(
                "select is_nullable from information_schema.columns "
                "where table_name = 'user_sessions' and column_name = 'last_seen_at'"
            )
        )
    return row == "NO"


async def _session(user: User) -> httpx.AsyncClient:
    """A signed-in client, with its session written straight to the table so it
    works the same on every database."""
    token = secrets.token_urlsafe(32)
    columns = "id, user_id, token_hash, expires_at, created_at"
    values = ":id, :user_id, :token_hash, :expires_at, :created_at"
    params = {
        "id": uuid.uuid4(),
        "user_id": user.id,
        "token_hash": hash_token(token),
        "expires_at": int(time.time()) + 3600,
        "created_at": int(time.time()),
    }
    if await _database_wants_last_seen():
        columns += ", last_seen_at"
        values += ", :seen"
        params["seen"] = int(time.time())
    async with SessionLocal() as db:
        await db.execute(text(f"insert into user_sessions ({columns}) values ({values})"), params)
        await db.commit()
    client = _client()
    client.headers["cookie"] = f"{session_cookie_name('test')}={token}"
    return client


async def test_a_new_password_ends_every_other_session(made) -> None:
    user = await made(f"pw_{uuid.uuid4().hex[:8]}")
    here = await _session(user)
    elsewhere = await _session(user)
    assert (await elsewhere.get("/api/auth/me")).status_code == 200

    changed = await here.patch(
        "/api/auth/me", json={"current_password": PASSWORD, "new_password": "Newer!Pass9"}
    )
    assert changed.status_code == 200, changed.text

    assert (await here.get("/api/auth/me")).status_code == 200  # the one that changed it stays
    assert (await elsewhere.get("/api/auth/me")).status_code == 401  # a stolen session does not


async def test_a_username_cannot_look_like_an_email(made) -> None:
    user = await made(f"at_{uuid.uuid4().hex[:8]}")
    client = await _session(user)
    response = await client.patch("/api/auth/me", json={"username": "someone@example.test"})
    assert response.status_code == 422


async def test_sign_in_prefers_the_exact_username(made) -> None:
    address = f"{uuid.uuid4().hex[:8]}@example.test"
    # an older account whose username is an address, and the account that owns that address
    squatter = await made(address, password=PASSWORD)
    owner = await made(f"own_{uuid.uuid4().hex[:8]}", email=address, password="Other!Pass9")
    assert squatter.id != owner.id
    if await _database_wants_last_seen():
        pytest.skip("this database needs a last_seen_at the app does not set, so sign-in cannot run on it")

    # the exact username matches the first account, never the address's owner
    signed_in = _client()
    ok = await signed_in.post(
        "/api/auth/login", json={"username_or_email": address, "password": PASSWORD}
    )
    assert ok.status_code == 200, ok.text
    assert (await signed_in.get("/api/auth/me")).json()["username"] == address
    wrong = _client()
    refused = await wrong.post(
        "/api/auth/login", json={"username_or_email": address, "password": "Other!Pass9"}
    )
    assert refused.status_code == 401


async def test_an_api_key_cannot_create_more_api_keys(made) -> None:
    user = await made(f"key_{uuid.uuid4().hex[:8]}")
    session = await _session(user)
    created = await session.post("/api/auth/api-keys", json={"name": "ci", "scopes": []})
    assert created.status_code == 200, created.text
    key = created.json()["api_key"]

    with_key = _client()
    refused = await with_key.post(
        "/api/auth/api-keys",
        json={"name": "more", "scopes": []},
        headers={"Authorization": f"Bearer {key}"},
    )
    assert refused.status_code == 403
