"""Credential updates preserve saved values and report validation through the public API."""

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.routes import settings as settings_routes
from src.core.auth import get_current_user
from src.core.crypto import decrypt_secret
from src.database.models.user import User
from src.database.session import get_db
from src.features.metadata.games.steam import SteamLibraryError
from src.main import app


@pytest.fixture
async def credentials():
    user = User(
        id=uuid4(), username="credentials", email="credentials@example.test", password_hash="x"
    )
    db = AsyncMock(spec=AsyncSession)

    async def database():
        yield db

    app.dependency_overrides[get_db] = database
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            yield client, db, user
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.parametrize(
    ("fields", "existing_id", "existing_key"),
    [
        ({"steam_id": "a" * 32, "api_key": "custom-profile"}, None, None),
        ({"steam_id": "custom-profile", "api_key": "  "}, None, "a" * 32),
        ({"api_key": "a" * 32}, "custom-profile", None),
    ],
)
async def test_steam_credentials_normalize_and_preserve_blank_fields(
    credentials, monkeypatch, fields, existing_id, existing_key
):
    client, db, user = credentials
    user.steam_id, user.steam_api_key = existing_id, existing_key
    resolver = Mock(return_value="76561198000000001")
    validator = Mock(
        return_value={"validated": True, "persona_name": "Player", "avatar_url": "image"}
    )
    monkeypatch.setattr(settings_routes.steam, "resolve_steam_id", resolver)
    monkeypatch.setattr(settings_routes, "_validate_provider", validator)
    response = await client.put("/api/settings/provider-credentials/Steam", json={"fields": fields})
    assert response.status_code == 200, response.text
    assert response.json() == {"provider": "Steam", "status": "connected", "detail": None}
    resolver.assert_called_once_with("custom-profile", "a" * 32)
    validator.assert_called_once_with("Steam", user)
    assert user.steam_id == "76561198000000001"
    assert user.steam_api_key == "a" * 32
    assert (user.steam_persona_name, user.steam_avatar_url) == ("Player", "image")
    assert db.commit.await_count == 3


async def test_incomplete_steam_credentials_are_saved_without_external_validation(
    credentials, monkeypatch
):
    client, db, user = credentials
    validator = Mock(side_effect=AssertionError("Incomplete credentials must not reach a provider"))
    monkeypatch.setattr(settings_routes, "_validate_provider", validator)
    response = await client.put(
        "/api/settings/provider-credentials/Steam", json={"fields": {"steam_id": "profile"}}
    )
    assert response.json() == {
        "provider": "Steam",
        "status": "saved",
        "detail": "Saved: now add your API key to connect.",
    }
    assert user.steam_id == "profile"
    validator.assert_not_called()
    db.commit.assert_awaited_once()


async def test_steam_resolution_failure_keeps_credentials_and_reports_error(
    credentials, monkeypatch
):
    client, db, user = credentials
    monkeypatch.setattr(
        settings_routes.steam, "resolve_steam_id", Mock(side_effect=SteamLibraryError("Not found"))
    )
    response = await client.put(
        "/api/settings/provider-credentials/Steam",
        json={"fields": {"steam_id": "profile", "api_key": "a" * 32}},
    )
    assert response.json() == {"provider": "Steam", "status": "error", "detail": "Not found"}
    assert (user.steam_id, user.steam_api_key) == ("profile", "a" * 32)
    db.commit.assert_awaited_once()


async def test_encrypted_provider_credentials_and_unknown_provider(credentials, monkeypatch):
    client, db, user = credentials
    monkeypatch.setattr(
        settings_routes, "_validate_provider", Mock(return_value={"validated": False})
    )
    response = await client.put(
        "/api/settings/provider-credentials/GOG", json={"fields": {"refresh_token": "  token  "}}
    )
    assert response.json() == {"provider": "GOG", "status": "saved", "detail": None}
    assert decrypt_secret(user.gog_refresh_token) == "token"
    db.commit.assert_awaited_once()
    response = await client.put("/api/settings/provider-credentials/unknown", json={"fields": {}})
    assert response.status_code == 400
    db.commit.assert_awaited_once()
