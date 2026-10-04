"""Version failures remain reviewable before package execution and during outages."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from test_plugin_install_sources import gate as _gate_fixture
from test_plugin_install_sources import package_bytes

from src.api.routes import plugins
from src.plugin_api.runtime_client import PluginRuntimeUnavailable

gate = _gate_fixture


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("contract", "sdk", "application", "expected"),
    [
        ("1.0.0", "*", "*", "whole plugin is stopped"),
        ("1.1.0", "^2.0.0", "*", "Host plugin SDK 1.1.0"),
        ("1.1.0", "*", "^2.0.0", "version 1.0.0"),
        ("1.1.0", "^1.1.0", "^1.0.0", ""),
    ],
)
async def test_verified_incompatible_package_has_reviewable_preview(
    gate, monkeypatch, contract, sdk, application, expected
):
    monkeypatch.setenv("PLUGIN_SDK_VERSION", "1.1.0")
    monkeypatch.setenv("PLUGIN_APPLICATION_VERSION", "1.0.0")
    payload = package_bytes(
        gate.plugin_id,
        trust="trusted",
        key=gate.key,
        api_contract_version=contract,
        sdk_range=sdk,
        application_range=application,
    )
    response = await gate.client.post(
        "/api/plugins/install/preview", files={"file": ("review.utp", payload)}
    )
    assert response.status_code == 200, response.text
    preview = response.json()
    assert preview["signature_verified"]
    assert preview["installable"] is (not expected)
    assert expected in preview["compatibility_reason"]
    assert preview["host_api_contract_version"] == "1.1.0"
    assert preview["host_sdk_version"] == "1.1.0"
    assert preview["host_application_version"] == "1.0.0"
    assert preview["sdk_version_range"] == sdk
    assert preview["application_version_range"] == application
    assert gate.registry.list() == []
    assert "start" not in gate.events


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["healthy", "mismatch", "missing", "offline"])
async def test_platform_reports_actual_versions_and_health(monkeypatch, state):
    monkeypatch.setenv("PLUGIN_SDK_VERSION", "1.1.0")
    monkeypatch.setenv("PLUGIN_APPLICATION_VERSION", "1.0.0")
    reported = {
        "available": True,
        "api_contract_version": "1.1.0",
        "sdk_version": "1.1.0",
        "application_version": "1.0.0",
    }
    if state == "mismatch":
        reported["api_contract_version"] = "1.0.0"
        reported["sdk_version"] = "2.0.0"
    if state == "missing":
        reported.pop("sdk_version")
    health = AsyncMock(
        return_value=reported,
        side_effect=PluginRuntimeUnavailable("Disconnected") if state == "offline" else None,
    )
    monkeypatch.setattr(plugins, "_client", SimpleNamespace(health=health))
    result = await plugins.runtime_health(SimpleNamespace())
    assert result["host_api_contract_version"] == "1.1.0"
    assert result["host_sdk_version"] == "1.1.0"
    assert result["host_application_version"] == "1.0.0"
    assert result["version_health"] == (
        "healthy" if state == "healthy" else "unavailable" if state == "offline" else "incompatible"
    )
    if state == "mismatch":
        assert "host 1.1.0, runtime 1.0.0" in result["version_error"]
        assert "host 1.1.0, runtime 2.0.0" in result["version_error"]
    elif state == "missing":
        assert "does not report its SDK" in result["version_error"]
    elif state == "offline":
        assert result["last_error"] == "Disconnected"
