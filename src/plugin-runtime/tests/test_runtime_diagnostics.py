"""Structured and redacted plugin runtime diagnostic coverage."""

import sys
import time
from datetime import datetime
from uuid import uuid4

from test_runtime import _package_bytes

from runtime import PluginRegistry, PluginSpec, PluginSupervisor


def test_diagnostics_are_structured_and_redact_sensitive_values(tmp_path) -> None:
    supervisor = PluginSupervisor(
        root=tmp_path / "work",
        storage_root=tmp_path / "storage",
    )

    supervisor._log(
        "example.plugin",
        "request failed token=super-secret https://hooks.example/api/webhooks/1/key",
        level="error",
        event="gateway.request_failed",
        correlation_id="request-1",
        metadata={"access_token": "also-secret", "attempt": 2},
    )

    event = supervisor.logs("example.plugin")[0]
    assert event["plugin_id"] == "example.plugin"
    assert event["level"] == "error"
    assert event["event"] == "gateway.request_failed"
    assert event["correlation_id"] == "request-1"
    assert event["metadata"] == {"access_token": "[REDACTED]", "attempt": 2}
    assert "super-secret" not in event["message"]
    assert "/webhooks/" not in event["message"]
    assert datetime.fromisoformat(event["timestamp"]).tzinfo is not None


def test_diagnostics_are_bounded_and_sequenced(tmp_path) -> None:
    supervisor = PluginSupervisor(
        root=tmp_path / "work",
        storage_root=tmp_path / "storage",
    )

    for index in range(205):
        supervisor._log("example.plugin", f"message {index}")

    events = supervisor.logs("example.plugin")
    assert len(events) == 200
    assert events[0]["sequence"] == 6
    assert events[-1]["sequence"] == 205
    assert events[-1]["message"] == "message 204"


def test_async_worker_failure_is_visible_and_clears_on_restart(
    tmp_path, monkeypatch
) -> None:
    """Real worker exits agree across manager/diagnostics without stale action errors."""
    monkeypatch.setenv("NONBUBBLE_ENV", "true")
    supervisor = PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    registry = PluginRegistry(tmp_path / "plugins", supervisor)
    registry.install_package(
        _package_bytes(), "worker.utp", installation_id=str(uuid4())
    )
    package = registry.package("example.upload")[0]
    registry._transition("example.upload", enabled=True, status="running")
    supervisor._log(
        "example.upload",
        "An unrelated action failed.",
        level="error",
        event="action.failed",
    )
    supervisor.start(
        PluginSpec(
            "example.upload",
            (
                sys.executable,
                "-c",
                "import time; time.sleep(0.05); raise SystemExit(9)",
            ),
        ),
        package,
    )
    try:
        deadline = time.monotonic() + 5
        while supervisor.running("example.upload") and time.monotonic() < deadline:
            time.sleep(0.01)
        failed = registry.diagnostics("example.upload")
        assert failed["status"] == "failed"
        assert failed["last_exit_code"] == 9
        assert "status 9" in failed["last_error"]
        assert "unrelated" not in failed["last_error"]
        assert registry.list()[0]["last_error"] == failed["last_error"]
        registry._transition(
            "example.upload", last_error="Explicit startup validation failed."
        )
        assert (
            registry.diagnostics("example.upload")["last_error"]
            == "Explicit startup validation failed."
        )
        registry._transition("example.upload", status="running", last_error=None)
        supervisor.start(
            PluginSpec(
                "example.upload", (sys.executable, "-c", "import time; time.sleep(60)")
            ),
            package,
        )
        restarted = registry.diagnostics("example.upload")
        assert restarted["status"] == "running"
        assert restarted["last_error"] is None
        assert restarted["last_exit_code"] is None
        registry.stop("example.upload", disable=False)
        stopped = registry.diagnostics("example.upload")
        assert stopped["status"] == "stopped"
        assert stopped["last_error"] is None
    finally:
        supervisor.stop("example.upload")
