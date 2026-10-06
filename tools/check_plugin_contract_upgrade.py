"""Verify the v1.0 restart boundary using actual companion archives and workers.

This check starts a verified historical worker as a simulated predecessor host,
then hands the installation to the current registry. No plugin implementation
or fake worker lives in this repository. No browser/media capture is produced.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _build_upgrade(
    plugins_root: Path, source: Path, plugin_id: str, old_version: str
) -> tuple[Path, str, bytes, str]:
    """Build a v1.1 archive with an owned disposable publisher, preserving real source."""
    for name in ("tools", "sdk", "publishers"):
        shutil.copytree(
            plugins_root / name,
            source / name,
            ignore=shutil.ignore_patterns("__pycache__"),
        )
    shutil.copytree(
        plugins_root / "examples/playtime-report",
        source / "examples/playtime-report",
    )
    manifest_path = source / "examples/playtime-report/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["api_contract_version"] == "1.1.0"
    major, minor, _ = map(int, old_version.split("."))
    manifest["version"] = f"{major}.{minor + 1}.0"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    key = Ed25519PrivateKey.generate()
    public = key.public_key().public_bytes_raw()
    key_id = "contract-upgrade-disposable"
    publisher = "Contract upgrade review"
    encoded = base64.b64encode(public).decode()
    record = {
        "key_id": key_id,
        "publisher": publisher,
        "channel": "demo",
        "status": "active",
        "plugin_id_prefixes": [plugin_id],
        "public_key_file": key_id + ".public-key.b64",
        "public_key_b64": encoded,
        "public_key_sha256": hashlib.sha256(public).hexdigest(),
    }
    (source / "publishers" / record["public_key_file"]).write_text(encoded, encoding="utf-8")
    registry_path = source / "publishers/registry.json"
    publishers = json.loads(registry_path.read_text(encoding="utf-8"))
    publishers["publishers"].append(record)
    registry_path.write_text(json.dumps(publishers), encoding="utf-8")
    release_path = source / "examples/playtime-report/release.json"
    release = json.loads(release_path.read_text(encoding="utf-8"))
    release["publisher"] = publisher
    release_path.write_text(json.dumps(release), encoding="utf-8")
    signing_env = {k: v for k, v in os.environ.items() if not k.startswith("PLUGIN_")}
    signing_env.update(
        PLUGIN_EXAMPLES_SIGNING_KEY_ID=key_id,
        PLUGIN_EXAMPLES_SIGNING_KEY_B64=base64.b64encode(key.private_bytes_raw()).decode(),
    )
    subprocess.run(
        [sys.executable, str(source / "tools/build_packages.py")],
        env=signing_env,
        check=True,
        capture_output=True,
    )
    migrated = source / ".validation/dist" / f"{plugin_id}-{manifest['version']}.utp"
    return migrated, key_id, public, publisher


def _legacy_archive(plugins_root: Path, plugin_id: str) -> Path:
    """Select a retained v1.0 release even after publication advances the catalogue."""
    catalogue = json.loads((plugins_root / "list.json").read_text(encoding="utf-8"))
    entry = next(item for item in catalogue["plugins"] if item["plugin_id"] == plugin_id)
    # Publication advances the catalogue to v1.1 while retaining signed v1.0
    # history. The predecessor test must select that historical contract.
    legacy_release = next(
        release
        for release in reversed(entry.get("releases", [entry]))
        if release["manifest"].get("api_contract_version", "1.0.0") == "1.0.0"
    )
    return plugins_root / "dist" / legacy_release["package"]["filename"]


def _extract_legacy(legacy: Path, package: Path) -> None:
    """Extract a verified historical archive to the owned predecessor installation."""
    package.mkdir(parents=True)
    with zipfile.ZipFile(legacy) as archive:
        (package / "manifest.json").write_bytes(archive.read("manifest.json"))
        for name in archive.namelist():
            if name.startswith("payload/") and not name.endswith("/"):
                target = package / name.removeprefix("payload/")
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(name))


def _prepare_predecessor(supervisor, package: Path, manifest) -> str:
    """Seed the old host's identity, storage and settings before its registry existed."""
    plugin_id = manifest.plugin_id
    installation_id = str(uuid4())
    supervisor._installation_ids[plugin_id] = installation_id
    supervisor._storage_quotas[plugin_id] = manifest.storage.quota_mb * 1024 * 1024
    supervisor._storage(plugin_id).put("retained/report", b"historical report")
    (package / ".settings.json").write_text('{"review":"kept"}', encoding="utf-8")
    return installation_id


def check(plugins_root: Path, work: Path) -> None:
    """Exercise a retained signed v1.0 worker and an actual verified v1.1 upgrade."""
    host = Path(__file__).resolve().parents[1]
    sys.path[:0] = [str(host / "src/backend"), str(host / "src/plugin-runtime")]
    from runtime import PluginRegistry, PluginSpec, PluginSupervisor
    from src.plugin_api.publisher_trust import load_trusted_publishers
    from src.plugin_api.updates import PluginPackageVerifier, TrustedPublisher

    work.mkdir(parents=True, exist_ok=False)
    plugin_id = "example.playtime-report"
    legacy = _legacy_archive(plugins_root, plugin_id)
    original_hash = hashlib.sha256(legacy.read_bytes()).hexdigest()
    verified = PluginPackageVerifier(
        load_trusted_publishers(plugins_root / "publishers/registry.json")
    ).inspect(legacy)
    assert verified.manifest.api_contract_version == "1.0.0"
    package = work / "installed" / plugin_id
    _extract_legacy(legacy, package)
    supervisor = PluginSupervisor(work / "workers", work / "storage")
    installation_id = _prepare_predecessor(supervisor, package, verified.manifest)
    try:
        # The predecessor predates the new registry gate. Start its real signed
        # main entrypoint before assigning the current registry callback.
        supervisor.start(
            PluginSpec(plugin_id, (sys.executable, "-c", "import plugin; plugin.main()")),
            package,
        )
        assert supervisor.running(plugin_id)
        registry = PluginRegistry(package.parent, supervisor)
        registry._transition(
            plugin_id, enabled=True, status="running", installation_id=installation_id
        )
        registry.restore_enabled()
        limited = registry.list()[0]
        assert limited["status"] == "running" and limited["enabled"]
        assert limited["compatible"] and limited["legacy_compatibility"]
        assert "old v1.0 UI" in limited["compatibility_warning"]
        assert supervisor.running(plugin_id)
        assert limited["installation_id"] == installation_id
        assert supervisor._storage(plugin_id).get("retained/report") == b"historical report"
        assert json.loads((package / ".settings.json").read_text(encoding="utf-8")) == {
            "review": "kept"
        }
        assert registry.ui(plugin_id).get("native_frontend") is None
        registry.stop(plugin_id)
        registry.start(plugin_id)
        assert registry.health(plugin_id)

        migrated, key_id, public, publisher = _build_upgrade(
            plugins_root, work / "source", plugin_id, verified.manifest.version
        )
        current = PluginPackageVerifier(
            {
                key_id: TrustedPublisher(
                    key_id,
                    public,
                    publisher,
                    plugin_id_prefixes=(plugin_id,),
                    require_manifest_binding=True,
                )
            }
        ).inspect(migrated)
        assert current.signing_version == 2
        registry.install_package(
            migrated.read_bytes(),
            migrated.name,
            installation_id=installation_id,
            replace=True,
            expected_version=verified.manifest.version,
        )
        registry.start(plugin_id)
        active = registry.list()[0]
        assert active["status"] == "running" and registry.health(plugin_id)
        assert active["api_contract_version"] == "1.1.0"
        assert active["installation_id"] == installation_id
        assert supervisor._storage(plugin_id).get("retained/report") == b"historical report"
        assert supervisor._settings(plugin_id) == {"review": "kept"}
        assert hashlib.sha256(legacy.read_bytes()).hexdigest() == original_hash
        (work / "conformance.json").write_text(
            json.dumps(
                {
                    "plugin_id": plugin_id,
                    "legacy_archive_sha256": original_hash,
                    "migrated_archive_sha256": hashlib.sha256(migrated.read_bytes()).hexdigest(),
                    "real_signed_legacy_worker_running_with_warning": True,
                    "legacy_stop_restart_supported": True,
                    "real_verified_v11_worker_running": True,
                    "identity_settings_storage_retained": True,
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(
            "Actual signed legacy worker runs with limited support; "
            "verified v1.1 update retains identity/settings/storage"
        )
    finally:
        supervisor.stop_all()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plugins-root", type=Path, required=True)
    parser.add_argument("--work-root", type=Path, required=True)
    arguments = parser.parse_args()
    check(arguments.plugins_root.resolve(), arguments.work_root.resolve())
