"""The private HTTP bridge preserves the public v1 JSON-line contract."""

import io
import json
import sys
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest
from runtime import (
    PluginSpec,
    PluginSupervisor,
    RuntimeGatewayError,
    RuntimePolicyError,
    gateway_error_response,
)


@pytest.fixture
def supervisor(tmp_path):
    instance = PluginSupervisor(
        tmp_path / "workers",
        tmp_path / "storage",
        gateway_url="http://replaceable-transport.example",
        gateway_token="x" * 32,
    )
    instance._installation_ids["contract"] = str(uuid4())
    instance._user_ids["contract"] = str(uuid4())
    return instance


@pytest.mark.parametrize("mode", ("abort", "handled", "retry_then_abort"))
def test_action_retains_only_an_unhandled_gateway_failure(
    supervisor, tmp_path, monkeypatch, mode
):
    """Exercise real JSON-line child exit behavior, including handled/retried errors."""
    monkeypatch.setenv("NONBUBBLE_ENV", "true")
    package = tmp_path / "protocol-action"
    package.mkdir()
    envelope = {
        "api_version": "v1",
        "request_id": str(uuid4()),
        "code": "forbidden",
        "message": "Administrator access is required.",
    }
    calls = []

    def dispatch(_plugin_id, message, **_kwargs):
        calls.append(message)
        if len(calls) == 1:
            raise RuntimeGatewayError(envelope)
        return {"payload": {"authorized": True}}

    monkeypatch.setattr(supervisor, "_handle_gateway_request", dispatch)
    statement = """
import json, sys
json.loads(sys.stdin.readline())
request = {'method': 'sessions.admin.list', 'capability': 'sessions.admin.read', 'payload': {}}
print(json.dumps(request), flush=True)
assert json.loads(sys.stdin.readline())['error']
if sys.argv[1] == 'handled':
    print(json.dumps({'plugin_action_result': {'handled': True}}), flush=True)
    sys.exit(0)
if sys.argv[1] == 'retry_then_abort':
    print(json.dumps(request), flush=True)
    assert json.loads(sys.stdin.readline())['payload']['authorized']
sys.exit(1)
"""
    spec = PluginSpec("contract", (sys.executable, "-c", statement, mode))
    if mode == "handled":
        assert json.loads(supervisor.execute(spec, package, b"{}")) == {"handled": True}
    elif mode == "abort":
        with pytest.raises(RuntimeGatewayError) as failure:
            supervisor.execute(spec, package, b"{}")
        assert failure.value.envelope == envelope
        assert failure.value.status_code == 403
    else:
        with pytest.raises(
            RuntimePolicyError, match="did not return a result"
        ) as failure:
            supervisor.execute(spec, package, b"{}")
        assert not isinstance(failure.value, RuntimeGatewayError)


@pytest.mark.parametrize(
    "code, status",
    (
        ("forbidden", 403),
        ("not_found", 404),
        ("invalid_request", 400),
        ("unavailable", 503),
        ("internal", 422),
        ({}, 422),
    ),
)
def test_gateway_failure_status_is_bounded_to_public_codes(code, status):
    assert (
        RuntimeGatewayError({"code": code, "message": "Rejected"}).status_code == status
    )


def test_gateway_preserves_supplied_correlation_and_accepts_legacy_response(
    supervisor, monkeypatch
):
    request_id = str(uuid4())

    def transport(request, *, timeout):
        assert timeout == 10
        body = json.loads(request.data)
        assert body["api_version"] == "v1" and body["request_id"] == request_id
        assert body["installation_id"] == supervisor._installation_ids["contract"]
        return io.BytesIO(b'{"payload":{"authorized":true}}')

    monkeypatch.setattr("runtime.urlopen", transport)
    response = supervisor._handle_gateway_request(
        "contract",
        {
            "request_id": request_id,
            "method": "capabilities.check",
            "capability": "games.read",
        },
    )
    assert response == {
        "api_version": "v1",
        "request_id": request_id,
        "payload": {"authorized": True},
    }


@pytest.mark.parametrize(
    "field,value", [("request_id", str(uuid4())), ("api_version", "v2")]
)
def test_gateway_rejects_wrong_version_or_correlation(
    supervisor, monkeypatch, field, value
):
    monkeypatch.setattr(
        "runtime.urlopen",
        lambda *args, **kwargs: io.BytesIO(
            json.dumps(
                {
                    "payload": {"authorized": True},
                    field: value,
                }
            ).encode()
        ),
    )
    with pytest.raises(RuntimePolicyError, match="correlation|unsupported API version"):
        supervisor._handle_gateway_request(
            "contract",
            {
                "method": "capabilities.check",
                "capability": "games.read",
            },
        )


def test_gateway_retains_permission_error_and_correlation_across_http(
    supervisor, monkeypatch
):
    request_id = str(uuid4())
    envelope = {
        "api_version": "v1",
        "request_id": request_id,
        "code": "forbidden",
        "message": "permission games.read has not been granted",
    }

    def transport(request, **kwargs):
        raise HTTPError(
            request.full_url,
            403,
            "Forbidden",
            {},
            io.BytesIO(json.dumps({"error": envelope}).encode()),
        )

    monkeypatch.setattr("runtime.urlopen", transport)
    request = {
        "request_id": request_id,
        "method": "games.list",
        "capability": "games.read",
    }
    with pytest.raises(RuntimeGatewayError) as failure:
        supervisor._handle_gateway_request("contract", request)
    response = gateway_error_response(failure.value, request)
    assert response["error"] == envelope["message"]
    assert response["error_detail"] == envelope
    assert response["request_id"] == request_id


def test_gateway_version_rejection_precedes_storage_and_http(supervisor, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Incompatible protocol must not reach host or storage")

    monkeypatch.setattr("runtime.urlopen", forbidden)
    monkeypatch.setattr(supervisor, "_storage", forbidden)
    with pytest.raises(RuntimeGatewayError) as failure:
        supervisor._handle_gateway_request(
            "contract",
            {
                "api_version": "v2",
                "method": "storage.put",
                "capability": "plugin.storage",
                "payload": {"key": "data", "value": "denied"},
            },
        )
    assert failure.value.envelope["code"] == "incompatible"


def test_gateway_network_failure_has_correlated_unavailable_error(
    supervisor, monkeypatch
):
    def unavailable(*args, **kwargs):
        raise TimeoutError("private transport details")

    monkeypatch.setattr("runtime.urlopen", unavailable)
    request = {"method": "games.list", "capability": "games.read"}
    with pytest.raises(RuntimeGatewayError) as failure:
        supervisor._handle_gateway_request("contract", request)
    response = gateway_error_response(failure.value, request)
    assert response["error_detail"]["code"] == "unavailable"
    assert response["request_id"] == request["request_id"]
    assert "private transport" not in response["error"]


@pytest.mark.parametrize(
    "exception, expected",
    (
        (TimeoutError("private transport details"), "timed out"),
        (URLError(TimeoutError("private transport details")), "timed out"),
        (
            URLError(ConnectionRefusedError("private transport details")),
            "connection was refused",
        ),
        (
            json.JSONDecodeError("private transport details", "secret", 0),
            "invalid JSON",
        ),
        (URLError("private transport details"), "is unavailable"),
    ),
)
def test_gateway_transport_diagnostics_are_actionable_and_redacted(
    supervisor, monkeypatch, exception, expected
):
    def unavailable(*args, **kwargs):
        raise exception

    monkeypatch.setattr("runtime.urlopen", unavailable)
    request = {"method": "games.list", "capability": "games.read"}
    with pytest.raises(RuntimeGatewayError) as failure:
        supervisor._handle_gateway_request("contract", request)
    response = gateway_error_response(failure.value, request)
    assert expected in response["error"]
    assert "Check " in response["error"]
    assert "private transport" not in response["error"]
    assert "secret" not in response["error"]
    assert response["error_detail"]["request_id"] == request["request_id"]
