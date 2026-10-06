"""Broker configuration is inherited only across authenticated private transport."""

import json
import threading
from contextlib import contextmanager
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from runtime import (
    PluginRegistry,
    PluginSupervisor,
    RuntimeGatewayError,
    RuntimeHandler,
    RuntimeServer,
)


@contextmanager
def running_runtime(tmp_path, gateway_url=None):
    """Serve the real private HTTP adapter with a disposable configuration."""
    token = "configuration-test-" + "x" * 32
    supervisor = PluginSupervisor(
        tmp_path / "work",
        tmp_path / "storage",
        gateway_url=gateway_url,
        gateway_token=token,
    )
    server = RuntimeServer(("127.0.0.1", 0), RuntimeHandler)
    server.registry = PluginRegistry(tmp_path / "plugins", supervisor)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield supervisor, f"http://127.0.0.1:{server.server_port}", token
    finally:
        server.shutdown()
        worker.join(timeout=5)
        server.server_close()


def health(address, token=None, callback=None):
    """Read the public/same authenticated health endpoint without retaining secrets."""
    headers = {}
    if token is not None:
        headers["X-Plugin-Runtime-Token"] = token
    if callback is not None:
        headers["X-Plugin-Gateway-URL"] = callback
    with urlopen(Request(address + "/health", headers=headers), timeout=5) as response:
        return json.load(response)


@pytest.fixture(autouse=True)
def private_transport_environment(monkeypatch):
    """Keep local machine configuration out of transport regression cases."""
    monkeypatch.delenv("PLUGIN_GATEWAY_URL", raising=False)
    monkeypatch.setenv("PLUGIN_RUNTIME_TOKEN", "configuration-test-" + "x" * 32)


def test_missing_runtime_callback_is_repaired_by_authenticated_host(tmp_path):
    """An app-only configured callback repairs a real running HTTP service."""
    with running_runtime(tmp_path) as (supervisor, address, token):
        initial = health(address)
        assert initial["gateway_configured"] is False
        assert "PLUGIN_GATEWAY_URL" in initial["gateway_error"]
        repaired = health(address, token, "http://private-app:8000/prefix/")
        assert repaired["gateway_configured"] is True
        assert repaired["gateway_configuration_source"] == "host"
        assert repaired["gateway_error"] is None
        assert supervisor.gateway_url == "http://private-app:8000/prefix"
        assert "private-app" not in json.dumps(repaired)
        assert token not in json.dumps(repaired)


@pytest.mark.parametrize("token", [None, "wrong-token"])
def test_unauthenticated_health_cannot_change_callback(tmp_path, token):
    """Anonymous health access cannot configure the privileged reverse transport."""
    with running_runtime(tmp_path) as (supervisor, address, _token):
        result = health(address, token, "http://attacker.invalid")
        assert result["gateway_configured"] is False
        assert supervisor.gateway_url == ""


def test_runtime_local_callback_wins_over_host_advertisement(tmp_path):
    """An explicit runtime deployment address retains precedence."""
    with running_runtime(tmp_path, "https://explicit.internal") as (
        supervisor,
        address,
        token,
    ):
        result = health(address, token, "http://other.internal")
        assert result["gateway_configuration_source"] == "runtime"
        assert supervisor.gateway_url == "https://explicit.internal"


@pytest.mark.parametrize(
    "callback",
    [
        "file:///private",
        "http://user:secret@internal",
        "http://internal?q=secret",
        "http://internal#fragment",
        "http://internal:bad",
        "http://internal:0",
    ],
)
def test_invalid_host_callback_is_rejected_without_disclosure(tmp_path, callback):
    """Invalid service configuration never forwards credentials or mutates state."""
    with running_runtime(tmp_path) as (supervisor, address, token):
        with pytest.raises(HTTPError) as failure:
            health(address, token, callback)
        with failure.value as response:
            assert response.code == 422
            assert json.load(response) == {
                "detail": "App PLUGIN_GATEWAY_URL is invalid."
            }
        assert supervisor.gateway_url == ""


def test_unconfigured_action_is_an_actionable_service_failure(tmp_path):
    """Missing deployment configuration is not a user's invalid plugin action."""
    supervisor = PluginSupervisor(
        tmp_path / "work", tmp_path / "storage", gateway_token="x" * 32
    )
    with pytest.raises(RuntimeGatewayError) as failure:
        supervisor._handle_gateway_request(
            "example.configuration",
            {"method": "games.list", "capability": "games.read"},
        )
    assert failure.value.status_code == 503
    assert failure.value.envelope["code"] == "unavailable"
    assert "PLUGIN_GATEWAY_URL" in str(failure.value)
