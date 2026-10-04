"""Rich release metadata must remain compatible with existing v1 catalogues."""

import ast
import hashlib
import inspect
import io
import json
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import BaseModel, Field
from test_plugin_install_sources import package_bytes

from src.api.routes import plugins
from src.plugin_api.installer import inspect_package
from src.plugin_api.updates import (
    PackageFormatError,
    PluginPackageVerifier,
    canonical_payload_digest,
)


def release_package(path, **changes):
    with zipfile.ZipFile(io.BytesIO(package_bytes("example.metadata"))) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        files = [("plugin.py", archive.read("payload/plugin.py"))]
    metadata = {
        "schema_version": 1,
        "version": "2.0.0",
        "tags": ["media", "integration"],
        "automatic_update": False,
        "release_notes": "Manual release",
        **changes,
    }
    files.append(("distribution.json", json.dumps(metadata).encode()))
    manifest["integrity"]["sha256"] = canonical_payload_digest(files)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest))
        for name, content in files:
            archive.writestr("payload/" + name, content)
    return inspect_package(path, PluginPackageVerifier(require_signature=False))


def test_preview_consumes_integrity_verified_release_metadata(tmp_path):
    inspected = release_package(tmp_path / "release.utp")
    preview = plugins._install_preview(inspected)
    assert preview["tags"] == ["media", "integration"]
    assert preview["automatic_update"] is False
    assert preview["release_notes"] == "Manual release"


@pytest.mark.parametrize(
    "changes",
    [
        {"version": "3.0.0"},
        {"automatic_update": "false"},
        {"tags": ["bad/tag"]},
        {"tags": ["media", "media"]},
        {"release_notes": "x" * 4001},
    ],
)
def test_invalid_packaged_release_metadata_is_rejected(tmp_path, changes):
    with pytest.raises(PackageFormatError, match="distribution metadata"):
        release_package(tmp_path / "release.utp", **changes)


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", ["version", "digest", "archive_hash", "url", "identity"])
async def test_catalogue_acquisition_rejects_mismatched_release(tmp_path, monkeypatch, defect):
    path = tmp_path / "release.utp"
    inspected = release_package(path)
    advertised = entry(
        sha256=inspected.package.payload_digest,
        package_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    field = {"archive_hash": "package_sha256", "digest": "sha256", "identity": "plugin_id"}.get(
        defect, defect
    )
    advertised[field] = {
        "version": "3.0.0",
        "digest": "0" * 64,
        "archive_hash": "0" * 64,
        "url": "https://packages.example/other.utp",
        "identity": "example.other",
    }[defect]

    async def catalogue(**kwargs):
        return [plugins.PluginCatalogEntry.model_validate(advertised)]

    monkeypatch.setattr(plugins, "plugin_catalog", catalogue)
    request = plugins.PluginInstallUrl(
        url="https://packages.example/plugin.utp",
        source_type="catalogue",
        catalogue_url="https://catalogue.example/list.json",
    )
    with pytest.raises(HTTPException) as failure:
        await plugins._validate_catalogue_candidate(path, inspected, request, SimpleNamespace())
    assert failure.value.status_code == 409


def entry(**changes):
    return {
        "plugin_id": "example.metadata",
        "name": "Metadata",
        "version": "2.0.0",
        "url": "https://packages.example/plugin.utp",
        **changes,
    }


def test_packaged_icons_release_hashes_tags_and_documentation_are_preserved(monkeypatch):
    monkeypatch.setattr(plugins, "_validate_remote_url", lambda url: url)
    records = plugins._catalog_entries(
        {
            "version": 1,
            "plugins": [
                entry(
                    icon={"path": "icon.svg", "sha256": "a" * 64},
                    build={"source_path": "examples/metadata"},
                    publisher="Publisher",
                    sha256="b" * 64,
                    package_sha256="c" * 64,
                    automatic_update=False,
                    tags=["media", "integration"],
                    readme="# Plugin documentation",
                    sdk_version_range="^1.0.0",
                    application_version_range="^1.0.0",
                    package={"format": "utp-v1", "size_bytes": 1000},
                )
            ],
        },
        source_url="https://catalogue.example/list.json",
    )
    record = records[0]
    assert record["icon"] == "https://catalogue.example/examples/metadata/icon.svg"
    assert record["icon_metadata"]["sha256"] == "a" * 64
    assert record["digest"] == "b" * 64
    assert record["package_sha256"] == "c" * 64
    assert record["automatic_update"] is False
    assert record["tags"] == ("media", "integration")
    assert record["readme"].startswith("# Plugin")
    assert record["publisher"] == "Publisher"
    assert "^1.0.0" in record["compatibility"]


@pytest.mark.parametrize("path", ["../icon.svg", "/icon.svg", "a\\icon.svg", "a//icon.svg"])
def test_catalogue_rejects_unsafe_packaged_icon_paths(path):
    with pytest.raises(HTTPException) as error:
        plugins._catalog_entries(
            {"version": 1, "plugins": [entry(icon={"path": path, "sha256": "a" * 64})]}
        )
    assert error.value.status_code == 502


def test_old_catalogue_without_release_metadata_remains_supported(monkeypatch):
    monkeypatch.setattr(plugins, "_validate_remote_url", lambda url: url)
    record = plugins._catalog_entries({"version": 1, "plugins": [entry()]})[0]
    assert record["version"] == "2.0.0"
    assert record["automatic_update"] is True
    assert record["icon"] is None


def test_catalogue_transport_model_remains_loadable_by_public_contract_tools():
    # The independent plugin repository validates transport metadata without
    # importing the host API server or requiring its database configuration.
    namespace = {
        "BaseModel": BaseModel,
        "Field": Field,
        "PluginDependency": plugins.PluginDependency,
    }
    source = (
        inspect.getsource(plugins.PluginCatalogRelease)
        + "\n"
        + inspect.getsource(plugins.PluginCatalogEntry)
    )
    exec(compile(ast.parse(source), "catalogue-contract", "exec"), namespace)
    model = namespace["PluginCatalogEntry"]
    validated = model.model_validate(
        entry(icon={"path": "icon.svg", "sha256": "a" * 64}, sha256="b" * 64)
    )
    assert validated.icon["path"] == "icon.svg"
    assert validated.digest == "b" * 64
    assert model.model_validate(entry(digest="c" * 64)).digest == "c" * 64


@pytest.mark.parametrize(
    "releases",
    [
        [{"version": "broken", "url": "https://packages.example/old.utp"}],
        [{"version": "3.0.0", "url": "https://packages.example/old.utp"}],
        [{"version": "1.0.0", "url": "https://packages.example/old.utp"}] * 2,
        [{"version": "2.0.0", "url": "https://packages.example/different.utp"}],
        [{"version": "1.0.0", "url": "https://packages.example/old.utp", "sha256": "wrong"}],
    ],
)
def test_invalid_catalogue_history_is_rejected(monkeypatch, releases):
    monkeypatch.setattr(plugins, "_validate_remote_url", lambda url: url)
    with pytest.raises(HTTPException):
        plugins._catalog_entries({"version": 1, "plugins": [entry(releases=releases)]})


@pytest.mark.asyncio
@pytest.mark.parametrize("defect", [None, "url", "digest", "archive_hash"])
async def test_retained_release_review_binds_package_and_derives_pin(tmp_path, monkeypatch, defect):
    path = tmp_path / "retained.utp"
    inspected = release_package(path)
    release = {
        "version": "2.0.0",
        "url": "https://packages.example/plugin.utp",
        "sha256": inspected.package.payload_digest,
        "package_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }
    if defect:
        release[{"digest": "sha256", "archive_hash": "package_sha256"}.get(defect, defect)] = (
            "https://packages.example/different.utp" if defect == "url" else "0" * 64
        )
    advertised = plugins.PluginCatalogEntry.model_validate(
        entry(version="3.0.0", url="https://packages.example/latest.utp", releases=[release])
    )

    async def catalogue(**kwargs):
        return [advertised]

    monkeypatch.setattr(plugins, "plugin_catalog", catalogue)
    request = plugins.PluginInstallUrl(
        url="https://packages.example/plugin.utp",
        source_type="catalogue",
        catalogue_url="https://catalogue.example/list.json",
    )
    if defect:
        with pytest.raises(HTTPException) as error:
            await plugins._validate_catalogue_candidate(path, inspected, request, SimpleNamespace())
        assert error.value.status_code == 409
    else:
        entries = await plugins._validate_catalogue_candidate(
            path, inspected, request, SimpleNamespace()
        )
        source = plugins._acquisition_source(request, inspected, entries)
        assert source["version_pin"] == "2.0.0"
        assert source["latest_version"] == "3.0.0"
        assert (
            plugins._install_preview(inspected, source=source)["source"]["version_pin"] == "2.0.0"
        )


@pytest.mark.parametrize(
    "channel,allowed,expected",
    [
        ("official", True, "official"),
        ("demo", True, "demo"),
        ("official", False, "unverified"),
        (None, False, "unverified"),
    ],
)
def test_catalogue_category_uses_scoped_registry_not_advertised_brand(
    monkeypatch, channel, allowed, expected
):
    monkeypatch.setattr(plugins, "_validate_remote_url", lambda url: url)
    publisher = SimpleNamespace(channel=channel, allows_plugin=lambda plugin_id: allowed)
    monkeypatch.setattr(
        plugins,
        "_plugin_package_verifier",
        lambda: SimpleNamespace(publishers={"key": publisher} if channel else {}),
    )
    record = plugins._catalog_entries(
        {
            "version": 1,
            "plugins": [
                entry(
                    name="Official plugin",
                    catalogue_channel="official",
                    publisher="Official",
                    tags=["official"],
                    signing={"key_id": "key"},
                )
            ],
        }
    )[0]
    assert record["catalogue_channel"] == expected
