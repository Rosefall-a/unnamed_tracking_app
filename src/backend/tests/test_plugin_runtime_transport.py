"""Valid isolated operations may finish after the lightweight health deadline."""

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

import pytest

from src.plugin_api import runtime_client


@pytest.fixture(name="slow_runtime")
def slow_runtime_server(monkeypatch):
    """Serve real slow HTTP responses without holding unrelated runtime resources."""
    token = "private-runtime-test-token-" + "x" * 32
    monkeypatch.setattr(
        runtime_client,
        "manager_state",
        lambda: SimpleNamespace(settings=lambda: {"reduced_isolation_acknowledged": False}),
    )

    class Handler(BaseHTTPRequestHandler):
        """Authenticate the private transport and return a bounded slow result."""

        def log_message(self, *_args):
            pass

        def do_POST(self):  # noqa: N802 - standard-library HTTP handler contract
            """Handle the standard-library method name for a POST request."""
            assert self.headers.get("X-Plugin-Runtime-Token") == token
            assert self.headers.get("X-Plugin-Reduced-Isolation-Acknowledged") == "false"
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(11)
            body = json.dumps({"completed": True}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield runtime_client.PluginRuntimeClient(
            base_url=f"http://127.0.0.1:{server.server_port}", token=token
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["action", "route"])
async def test_valid_operation_outlives_health_timeout(slow_runtime, operation):
    """Both public client operations retain valid results beyond the health deadline."""
    if operation == "action":
        result = await slow_runtime.action("example.slow", "get-config", {})
    else:
        result = await slow_runtime.route("example.slow", "settings", {}, user_id="test-user")
    assert result == {"completed": True}
