"""A server acknowledgement enables fallback without an environment override."""

import json
import sys
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest
from runtime import PluginRegistry, PluginSpec, PluginSupervisor, RuntimeHandler, RuntimeServer
from test_runtime import _package_bytes


def test_admin_acknowledgement_starts_real_worker_and_survives_restart(tmp_path, monkeypatch):
    monkeypatch.delenv("NONBUBBLE_ENV", raising=False)
    supervisor = PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    supervisor.isolation["bubblewrap_available"] = False
    registry = PluginRegistry(tmp_path / "plugins", supervisor)
    registry.acknowledge_reduced_isolation(True)
    process = supervisor.start(
        PluginSpec("example.approved", (sys.executable, "-c", "import time; time.sleep(60)")),
        tmp_path,
    )
    try:
        assert process.poll() is None
        assert supervisor.isolation["reduced_isolation_allowed"] is True
        assert supervisor.isolation["reduced_isolation_env_override"] is False
        reloaded = PluginRegistry(
            registry.root, PluginSupervisor(tmp_path / "new-work", supervisor.storage_root)
        )
        assert reloaded.supervisor.reduced_isolation_acknowledged is True
    finally:
        supervisor.stop_all()


def test_withdrawing_acknowledgement_stops_workers_and_preserves_installation(
    tmp_path, monkeypatch
):
    monkeypatch.delenv("NONBUBBLE_ENV", raising=False)
    supervisor = PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    supervisor.isolation["bubblewrap_available"] = False
    registry = PluginRegistry(tmp_path / "plugins", supervisor)
    registry.install_package(_package_bytes(), "worker.utp", installation_id=str(uuid4()))
    registry.acknowledge_reduced_isolation(True)
    registry.start("example.upload")
    try:
        assert supervisor.running("example.upload")
        registry.acknowledge_reduced_isolation(False)
        assert not supervisor.running("example.upload")
        installed = registry.list()[0]
        assert installed["enabled"] and installed["status"] == "failed"
        assert "withdrawn" in installed["last_error"]
        assert registry.package("example.upload")[0].is_dir()
    finally:
        supervisor.stop_all()


def test_acknowledged_fallback_loads_package_modules_for_actions(tmp_path, monkeypatch):
    monkeypatch.delenv("NONBUBBLE_ENV", raising=False)
    package = tmp_path / "package"
    package.mkdir()
    (package / "action_module.py").write_text("VALUE = 'package loaded'\n", encoding="utf-8")
    supervisor = PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    supervisor.isolation["bubblewrap_available"] = False
    supervisor.reduced_isolation_acknowledged = True
    result = supervisor.execute(
        PluginSpec(
            "example.action",
            (
                sys.executable,
                "-c",
                "import action_module,json; print(json.dumps({'plugin_action_result': {'value': action_module.VALUE}}))",
            ),
        ),
        package,
        b"{}",
        timeout=5,
    )
    assert json.loads(result) == {"value": "package loaded"}


def test_acknowledgement_keeps_bubblewrap_when_usable(tmp_path, monkeypatch):
    monkeypatch.delenv("NONBUBBLE_ENV", raising=False)
    supervisor = PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    supervisor.isolation["bubblewrap_available"] = True
    registry = PluginRegistry(tmp_path / "plugins", supervisor)
    registry.acknowledge_reduced_isolation(True)
    command = supervisor._sandbox_command(
        PluginSpec("example.secure", ("python", "plugin.py")), tmp_path, tmp_path
    )
    assert command[0] == "bwrap"
    assert supervisor.isolation["reduced_isolation_allowed"] is False


def test_public_health_cannot_approve_isolation_without_runtime_credentials(tmp_path, monkeypatch):
    token = "runtime-test-credential-" + "a" * 32
    monkeypatch.setenv("PLUGIN_RUNTIME_TOKEN", token)
    monkeypatch.delenv("NONBUBBLE_ENV", raising=False)
    registry = PluginRegistry(
        tmp_path / "plugins", PluginSupervisor(tmp_path / "work", tmp_path / "storage")
    )
    registry.supervisor.isolation["bubblewrap_available"] = False
    server = RuntimeServer(("127.0.0.1", 0), RuntimeHandler)
    server.registry = registry
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}/health"
    try:
        with urlopen(
            Request(url, headers={"X-Plugin-Reduced-Isolation-Acknowledged": "true"}), timeout=5
        ) as response:
            assert response.status == 200
        assert registry.supervisor.reduced_isolation_acknowledged is False
        with urlopen(
            Request(
                url,
                headers={
                    "X-Plugin-Runtime-Token": token,
                    "X-Plugin-Reduced-Isolation-Acknowledged": "true",
                },
            ),
            timeout=5,
        ) as response:
            assert json.loads(response.read())["reduced_isolation_allowed"] is True
        assert registry.supervisor.reduced_isolation_acknowledged is True

        def fail_policy(_acknowledged):
            raise OSError("policy storage is read-only")

        monkeypatch.setattr(registry, "acknowledge_reduced_isolation", fail_policy)
        with pytest.raises(HTTPError) as failure:
            urlopen(
                Request(
                    url,
                    headers={
                        "X-Plugin-Runtime-Token": token,
                        "X-Plugin-Reduced-Isolation-Acknowledged": "false",
                    },
                ),
                timeout=5,
            )
        assert failure.value.code == 503
        assert "policy storage is read-only" in json.loads(failure.value.read())["detail"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
