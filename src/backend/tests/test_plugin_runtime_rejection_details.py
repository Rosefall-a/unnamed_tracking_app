"""Public native actions retain bounded runtime failures rather than generic 422 errors."""

from types import SimpleNamespace

import httpx
import pytest

from src.api.routes.plugin_manager.runtime import runtime_request_error
from src.plugin_api import runtime_client


@pytest.mark.parametrize(
    "status, detail",
    (
        (403, "Administrator access is required."),
        (404, "session not found or already revoked"),
        (400, "session_id must be a UUID"),
    ),
)
async def test_runtime_rejection_reaches_host_with_its_public_status(monkeypatch, status, detail):
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(status, json={"detail": detail})
    )
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        runtime_client.httpx,
        "AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )
    monkeypatch.setattr(
        runtime_client, "manager_state", lambda: SimpleNamespace(settings=lambda: {})
    )
    client = runtime_client.PluginRuntimeClient("http://isolated-runtime", "x" * 32)
    with pytest.raises(runtime_client.PluginRuntimeRequestError) as failure:
        await client.action("example.protocol", "list", {})
    response = runtime_request_error(failure.value)
    assert response.status_code == status and response.detail == detail


def test_legacy_runtime_rejection_defaults_to_existing_policy_status():
    response = runtime_request_error(
        runtime_client.PluginRuntimeRequestError("Runtime policy rejected the operation.")
    )
    assert response.status_code == 422 and "policy rejected" in response.detail
