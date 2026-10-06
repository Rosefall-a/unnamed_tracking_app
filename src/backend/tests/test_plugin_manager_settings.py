"""Host-owned manager settings stay editable during a runtime outage."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.routes import plugins
from src.api.routes.plugin_manager import lifecycle as plugin_lifecycle
from src.api.routes.plugin_manager import runtime as plugin_runtime
from src.plugin_api.manager_state import ManagerState
from src.plugin_api.runtime_client import PluginRuntimeClient, PluginRuntimeUnavailable


@pytest.mark.asyncio
async def test_settings_save_during_runtime_outage_and_survive_reload(tmp_path, monkeypatch):
    store = ManagerState(tmp_path / "manager.json")
    store.patch("example.retained", version="1.0.0", installation_id="existing-identity")
    monkeypatch.setattr(plugin_lifecycle, "manager_state", lambda: store)
    runtime = SimpleNamespace(
        plugins=AsyncMock(side_effect=PluginRuntimeUnavailable("offline")),
        prune_history=AsyncMock(),
    )
    monkeypatch.setattr(plugin_runtime, "_client", runtime)
    app = FastAPI()
    app.include_router(plugins.router)
    app.dependency_overrides[plugins.get_plugin_manager_admin] = lambda: SimpleNamespace()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/api/plugins/manager-settings",
            json={"automatic_updates": True, "retained_versions": 3},
        )
        assert response.status_code == 200
        assert response.json()["history_pruning_deferred"] is True
        assert (await client.get("/api/plugins/manager-settings")).json() == {
            "automatic_updates": True,
            "retained_versions": 3,
        }
        assert (
            await client.put("/api/plugins/manager-settings", json={"retained_versions": 0})
        ).status_code == 422
    runtime.prune_history.assert_not_awaited()
    reloaded = ManagerState(store.path)
    assert reloaded.settings()["retained_versions"] == 3
    assert reloaded.read()["plugins"]["example.retained"]["installation_id"] == "existing-identity"


@pytest.mark.asyncio
async def test_connected_save_applies_history_limit(tmp_path, monkeypatch):
    store = ManagerState(tmp_path / "manager.json")
    monkeypatch.setattr(plugin_lifecycle, "manager_state", lambda: store)
    runtime = SimpleNamespace(
        plugins=AsyncMock(return_value=[{"plugin_id": "example.retained"}]),
        prune_history=AsyncMock(),
    )
    monkeypatch.setattr(plugin_runtime, "_client", runtime)
    result = await plugins.save_manager_settings(
        plugins.ManagerSettingsIn(retained_versions=2), SimpleNamespace()
    )
    assert result["history_pruning_deferred"] is False
    runtime.prune_history.assert_awaited_once_with("example.retained", 2)


@pytest.mark.asyncio
async def test_reduced_isolation_approval_is_admin_owned_and_persisted(tmp_path, monkeypatch):
    store = ManagerState(tmp_path / "manager.json")
    monkeypatch.setattr(plugin_lifecycle, "manager_state", lambda: store)
    monkeypatch.setenv("PLUGIN_MANAGER_STATE_PATH", str(store.path))
    transport = SimpleNamespace(plugins=AsyncMock(return_value=[]), prune_history=AsyncMock())
    monkeypatch.setattr(plugin_runtime, "_client", transport)
    app = FastAPI()
    app.include_router(plugins.router)
    actor = uuid4()
    app.dependency_overrides[plugins.get_plugin_manager_admin] = lambda: SimpleNamespace(id=actor)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (
            await client.put(
                "/api/plugins/manager-settings", json={"reduced_isolation_acknowledged": "yes"}
            )
        ).status_code == 422
        assert (
            await client.put(
                "/api/plugins/manager-settings", json={"reduced_isolation_acknowledged": True}
            )
        ).status_code == 200
        assert store.settings()["reduced_isolation_acknowledged_by"] == str(actor)
        bridge = PluginRuntimeClient(token="test-token-" + "x" * 32)
        assert bridge._headers()["X-Plugin-Reduced-Isolation-Acknowledged"] == "true"
        assert ManagerState(store.path).settings()["reduced_isolation_acknowledged"] is True
        assert (
            await client.put(
                "/api/plugins/manager-settings", json={"reduced_isolation_acknowledged": False}
            )
        ).status_code == 200
        assert bridge._headers()["X-Plugin-Reduced-Isolation-Acknowledged"] == "false"


@pytest.mark.asyncio
async def test_reduced_isolation_approval_requires_admin_authentication():
    app = FastAPI()
    app.include_router(plugins.router)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.put(
            "/api/plugins/manager-settings", json={"reduced_isolation_acknowledged": True}
        )
    assert response.status_code in {401, 403}
