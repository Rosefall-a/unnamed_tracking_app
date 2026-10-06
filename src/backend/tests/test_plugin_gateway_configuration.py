"""The app advertises explicit private callbacks and preserves service repair guidance."""

from types import SimpleNamespace

import httpx
import pytest

from src.plugin_api import runtime_client


@pytest.mark.parametrize("gateway_url", [None, "", " http://private-app:8000/ "])
async def test_runtime_requests_advertise_only_configured_callback(monkeypatch, gateway_url):
    """The host callback never comes from the browser's URL or untrusted headers."""
    if gateway_url is None:
        monkeypatch.delenv("PLUGIN_GATEWAY_URL", raising=False)
    else:
        monkeypatch.setenv("PLUGIN_GATEWAY_URL", gateway_url)
    monkeypatch.setattr(
        runtime_client, "manager_state", lambda: SimpleNamespace(settings=lambda: {})
    )

    def response(request):
        assert request.headers["X-Plugin-Runtime-Token"] == "x" * 32
        assert request.headers.get("X-Plugin-Gateway-URL") == (
            "http://private-app:8000" if gateway_url else None
        )
        return httpx.Response(200, json={"available": True})

    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        runtime_client.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(response), **kwargs),
    )
    bridge = runtime_client.PluginRuntimeClient("http://private-runtime", "x" * 32)
    assert await bridge.health() == {"available": True}


async def test_runtime_service_error_retains_bounded_repair_message(monkeypatch):
    """Native pages receive the runtime's public guidance, without raw JSON wrappers."""
    message = "Set PLUGIN_GATEWAY_URL on the runtime or app service."
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        runtime_client.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(
            transport=httpx.MockTransport(
                lambda _request: httpx.Response(503, json={"detail": message})
            ),
            **kwargs,
        ),
    )
    monkeypatch.setattr(
        runtime_client, "manager_state", lambda: SimpleNamespace(settings=lambda: {})
    )
    bridge = runtime_client.PluginRuntimeClient("http://private-runtime", "x" * 32)
    with pytest.raises(runtime_client.PluginRuntimeUnavailable) as failure:
        await bridge.action("example.configuration", "list", {})
    assert str(failure.value) == message
