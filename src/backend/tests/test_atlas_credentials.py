"""Saving, showing and removing the Atlas connection under Settings."""

import uuid

import httpx
import pytest
from fastapi import Depends
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes import settings as settings_routes
from src.core.auth import get_current_user
from src.core.crypto import decrypt_secret
from src.database.models.user import User
from src.database.session import SessionLocal, get_db
from src.features.metadata.games.atlas import AtlasError
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
        await db.commit()
        user_id = user.id

    async def current_user(db: AsyncSession = Depends(get_db)) -> User:
        found = await db.get(User, user_id)
        assert found is not None
        return found

    app.dependency_overrides[get_current_user] = current_user
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        http.user_id = user_id  # type: ignore[attr-defined]
        yield http
    app.dependency_overrides.pop(get_current_user, None)
    async with SessionLocal() as db:
        await db.execute(delete(User).where(User.id == user_id))
        await db.commit()


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Every name resolves to a LAN address, and a node always accepts the token."""
    monkeypatch.setattr(
        "src.features.metadata.games.atlas.socket.getaddrinfo",
        lambda host, port, **kwargs: [(2, 0, 0, "", ("192.168.1.20", port))],
    )

    class AcceptingClient:
        def __init__(self, base_url: str, token: str) -> None:
            assert base_url and token

        def validate(self) -> dict:
            return {"validated": True, "node_name": "Home"}

    monkeypatch.setattr(settings_routes, "AtlasClient", AcceptingClient)


async def _saved_user(client) -> User:
    async with SessionLocal() as db:
        user = await db.get(User, client.user_id)
        assert user is not None
        return user


async def test_saving_atlas_stores_a_plain_address_and_an_encrypted_token(client) -> None:
    response = await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": " https://atlas.example.test/api/v2/ ", "token": "secret-1"}},
    )

    assert response.json() == {"provider": "Atlas", "status": "connected", "detail": None}
    user = await _saved_user(client)
    assert user.atlas_base_url == "https://atlas.example.test"
    assert user.atlas_token and user.atlas_token != "secret-1"
    assert decrypt_secret(user.atlas_token) == "secret-1"


async def test_status_shows_the_address_but_never_the_token(client) -> None:
    await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "https://atlas.example.test", "token": "secret-1"}},
    )

    status = (await client.get("/api/settings/provider-credentials")).json()["Atlas"]

    assert status == {
        "status": "configured",
        "fields": {"base_url": "https://atlas.example.test"},
    }
    assert "secret-1" not in str(status)


async def test_a_refused_address_is_not_saved(client) -> None:
    response = await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "http://169.254.169.254/", "token": "secret-1"}},
    )

    assert response.json()["status"] == "error"
    user = await _saved_user(client)
    assert user.atlas_base_url is None


async def test_a_node_that_rejects_the_token_reports_the_error(client, monkeypatch) -> None:
    class RejectingClient:
        def __init__(self, base_url: str, token: str) -> None:
            pass

        def validate(self) -> dict:
            raise AtlasError("Atlas rejected the token.")

    monkeypatch.setattr(settings_routes, "AtlasClient", RejectingClient)

    response = await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "https://atlas.example.test", "token": "wrong"}},
    )

    assert response.json() == {
        "provider": "Atlas",
        "status": "error",
        "detail": "Atlas rejected the token.",
    }


async def test_connecting_adds_atlas_to_an_order_saved_before_it_existed(client) -> None:
    old_order = ["IGDB", "Steam"]
    await client.put("/api/settings/scan", json={"provider_order": old_order})

    await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "https://atlas.example.test", "token": "secret-1"}},
    )
    scan = (await client.get("/api/settings/scan")).json()
    assert scan["provider_order"] == [*old_order, "Atlas"]

    # connecting again leaves the order alone, including a place the user moved it to
    await client.put("/api/settings/scan", json={"provider_order": ["Atlas", "IGDB"]})
    await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "https://atlas.example.test", "token": "secret-2"}},
    )
    scan = (await client.get("/api/settings/scan")).json()
    assert scan["provider_order"] == ["Atlas", "IGDB"]


async def test_atlas_can_be_ordered_and_disconnected(client) -> None:
    response = await client.put(
        "/api/settings/scan", json={"provider_order": ["Atlas", "IGDB", "Steam", "GOG", "GiantBomb", "RetroAchievements", "HowLongToBeat"]}
    )
    assert response.status_code == 200

    await client.put(
        "/api/settings/provider-credentials/Atlas",
        json={"fields": {"base_url": "https://atlas.example.test", "token": "secret-1"}},
    )
    removed = await client.delete("/api/settings/provider-credentials/Atlas")

    assert removed.json() == {"provider": "Atlas", "status": "not_configured"}
    user = await _saved_user(client)
    assert user.atlas_base_url is None and user.atlas_token is None
