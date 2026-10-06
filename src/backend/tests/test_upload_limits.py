"""Administrator limit changes preserve other caps and their environment fallbacks."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes.settings import router
from src.core.app_integrations import UPLOAD_LIMIT_FIELDS
from src.core.auth import get_current_user
from src.core.config import settings
from src.database.session import get_db


@pytest.fixture
def boundary():
    row = SimpleNamespace(**dict.fromkeys(UPLOAD_LIMIT_FIELDS), tmdb_api_key="unchanged")
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    user = SimpleNamespace(is_admin=True)
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    return app, row, db, user


@pytest.mark.asyncio
async def test_environment_defaults_and_partial_update_reset(boundary):
    app, row, db, _ = boundary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        defaults = (await client.get("/api/settings/upload-limits")).json()
        assert defaults == {name: getattr(settings, name.upper()) for name in UPLOAD_LIMIT_FIELDS}
        response = await client.put(
            "/api/settings/upload-limit", json={"max_clip_size_mb": 3, "max_world_save_size_mb": 7}
        )
        assert response.status_code == 200
        assert response.json() == {**defaults, "max_clip_size_mb": 3, "max_world_save_size_mb": 7}
        response = await client.put("/api/settings/upload-limit", json={"max_clip_size_mb": None})
        assert response.json() == {**defaults, "max_world_save_size_mb": 7}
        assert row.max_upload_size_mb is None
        assert row.max_save_archive_size_mb is None
        assert row.tmdb_api_key == "unchanged"
    assert db.commit.await_count == 2


@pytest.mark.asyncio
async def test_member_can_read_but_cannot_change_any_limit(boundary):
    app, _, db, user = boundary
    user.is_admin = False
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.get("/api/settings/upload-limits")).status_code == 200
        for name in UPLOAD_LIMIT_FIELDS:
            assert (
                await client.put("/api/settings/upload-limit", json={name: 1})
            ).status_code == 403
    db.commit.assert_not_awaited()


@pytest.mark.parametrize("value", [0, -1, 1.5, "2", True, 2147483648])
@pytest.mark.asyncio
async def test_invalid_caps_are_rejected_without_partial_writes(boundary, value):
    app, row, db, _ = boundary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for name in UPLOAD_LIMIT_FIELDS:
            response = await client.put("/api/settings/upload-limit", json={name: value})
            assert response.status_code == 422
            assert getattr(row, name) is None
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_unknown_cap_is_not_silently_ignored(boundary):
    app, _, db, _ = boundary
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put("/api/settings/upload-limit", json={"max_plugin_size_mb": 10})
        assert response.status_code == 422
    db.commit.assert_not_awaited()
