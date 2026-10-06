"""Lifecycle failures preserve actionable runtime errors at the HTTP boundary."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from src.api.routes import plugins
from src.api.routes.plugin_manager import lifecycle, runtime
from src.plugin_api.contracts import PLUGIN_API_CONTRACT_VERSION
from src.plugin_api.manager_state import ManagerState
from src.plugin_api.runtime_client import PluginRuntimeRequestError, PluginRuntimeUnavailable


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "path,method,failing_call",
    [
        ("enable", "POST", "start"),
        ("start", "POST", "start"),
        ("retry", "POST", "start"),
        ("disable", "POST", "stop"),
        ("stop", "POST", "stop_runtime"),
        ("logs", "GET", "logs"),
        (f"history/{uuid4()}", "DELETE", "prune_history"),
        ("enable", "POST", "plugins"),
        ("start", "POST", "plugins"),
        ("retry", "POST", "plugins"),
        ("stop", "POST", "plugins"),
    ],
)
@pytest.mark.parametrize(
    "error_type,status,message",
    [
        (
            PluginRuntimeRequestError,
            422,
            "Bubblewrap is unavailable. Set NONBUBBLE_ENV=true on plugin-runtime and recreate it.",
        ),
        (PluginRuntimeUnavailable, 503, "The plugin runtime is unreachable."),
    ],
)
async def test_lifecycle_runtime_errors_are_visible(
    tmp_path, monkeypatch, path, method, failing_call, error_type, status, message
):
    installed = {
        "plugin_id": "example.error-report",
        "installation_id": str(uuid4()),
        "api_contract_version": PLUGIN_API_CONTRACT_VERSION,
        "enabled": True,
        "compatible": True,
    }
    transport = SimpleNamespace(
        plugins=AsyncMock(return_value=[installed]),
        start=AsyncMock(),
        stop=AsyncMock(),
        stop_runtime=AsyncMock(),
        logs=AsyncMock(),
        prune_history=AsyncMock(),
    )
    getattr(transport, failing_call).side_effect = error_type(message)
    monkeypatch.setattr(runtime, "_client", transport)
    monkeypatch.setattr(lifecycle, "manager_state", lambda: ManagerState(tmp_path / "manager.json"))
    app = FastAPI()
    app.include_router(plugins.router)
    app.dependency_overrides[plugins.get_plugin_manager_admin] = lambda: SimpleNamespace(id=uuid4())
    database = SimpleNamespace(scalar=AsyncMock(return_value=None))
    app.dependency_overrides[plugins.get_db] = lambda: database
    # A real HTTP request must receive JSON, rather than an unhandled exception/500.
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test"
    ) as client:
        response = await client.request(method, f"/api/plugins/{installed['plugin_id']}/{path}")
    assert response.status_code == status, response.text
    assert response.json()["detail"] == message
