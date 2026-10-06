"""Real inert archive installation, persistence, public assets and administrator boundaries."""

import io
import json
import stat
import zipfile
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes.themes import router
from src.core.auth import get_current_user
from src.core.theme_packages import ThemeStore, get_theme_store, inspect_theme_package

MANIFEST = {
    "format_version": 1,
    "id": "example.testing",
    "name": "Review Theme",
    "version": "1.0.0",
    "publisher": "Review publisher",
    "description": "An inert CSS review.",
    "kind": "example",
    "stylesheet": "theme.css",
    "supports": ["light", "dark"],
}


def package_bytes(manifest=None, additions=()) -> bytes:
    """Create actual ZIP inputs, including adversarial members when requested."""
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("manifest.json", json.dumps(manifest or MANIFEST))
        archive.writestr("theme.css", "html { --ui-radius-card: 0px; }")
        archive.writestr("assets/mark.svg", '<svg xmlns="http://www.w3.org/2000/svg"/>')
        for name, data in additions:
            archive.writestr(name, data)
    return output.getvalue()


def test_real_install_default_toggle_assets_and_removal_survive_reopening(tmp_path):
    store = ThemeStore(tmp_path)
    package = inspect_theme_package(package_bytes())
    store.install(package)
    store.set_default(MANIFEST["id"])
    reopened = ThemeStore(tmp_path)
    assert reopened.catalogue()["default_theme"] == MANIFEST["id"]
    assert (
        reopened.asset(MANIFEST["id"], package.digest, "theme.css").read_bytes()
        == package.files["theme.css"]
    )
    reopened.configure(MANIFEST["id"], False)
    assert reopened.catalogue() == {"default_theme": "native", "themes": []}
    assert len(reopened.catalogue(administration=True)["themes"]) == 1
    with pytest.raises(KeyError):
        reopened.asset(MANIFEST["id"], package.digest, "theme.css")
    reopened.configure(MANIFEST["id"], True)
    reopened.set_default(MANIFEST["id"])
    reopened.remove(MANIFEST["id"])
    assert store.catalogue() == {"default_theme": "native", "themes": []}
    assert not (tmp_path / "packages" / MANIFEST["id"]).exists()


@pytest.mark.parametrize(
    "name",
    [
        "../outside.css",
        "/outside.css",
        "assets/../../outside.css",
        "C:\\outside.css",
        "worker.py",
        "script.js",
    ],
)
def test_archive_paths_and_executable_files_are_rejected(name):
    with pytest.raises(ValueError):
        inspect_theme_package(package_bytes(additions=[(name, b"invalid")]))


def test_duplicate_paths_and_symlinks_are_rejected():
    with pytest.warns(UserWarning, match="Duplicate name"):
        data = package_bytes(additions=[("theme.css", b"replaced")])
    with pytest.raises(ValueError, match="duplicate"):
        inspect_theme_package(data)
    link = zipfile.ZipInfo("assets/link.css")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with pytest.raises(ValueError, match="links"):
        inspect_theme_package(package_bytes(additions=[(link, b"../../outside.css")]))


def test_corrupt_or_oversized_inputs_and_manifest_extensions_are_rejected():
    for data in [
        b"not a ZIP",
        b"x" * (10 * 1024 * 1024 + 1),
        package_bytes({**MANIFEST, "entrypoint": "worker.py"}),
        package_bytes({**MANIFEST, "format_version": True}),
    ]:
        with pytest.raises(ValueError):
            inspect_theme_package(data)
    with pytest.raises(ValueError, match="too large"):
        inspect_theme_package(package_bytes(additions=[("large.css", b"x" * (1024 * 1024 + 1))]))


def test_invalid_default_and_asset_digest_cannot_select_uninstalled_files(tmp_path):
    store = ThemeStore(tmp_path)
    package = inspect_theme_package(package_bytes())
    store.install(package)
    with pytest.raises(ValueError):
        store.set_default("not-installed")
    with pytest.raises(KeyError):
        store.asset(MANIFEST["id"], "different-digest", "theme.css")
    with pytest.raises(ValueError):
        store.asset(MANIFEST["id"], package.digest, "../index.json")


def test_http_admin_mutations_and_public_prelogin_assets(tmp_path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_theme_store] = lambda: ThemeStore(tmp_path)
    user = SimpleNamespace(is_admin=False)
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        upload = {"file": ("review.utt", package_bytes())}
        assert client.get("/api/themes").json() == {"default_theme": "native", "themes": []}
        assert client.get("/api/themes/manage").status_code == 403
        assert client.post("/api/themes/install", files=upload).status_code == 403
        user.is_admin = True
        preview = client.post("/api/themes/install/preview", files=upload)
        assert preview.status_code == 200
        installed = client.post("/api/themes/install", files=upload)
        assert installed.status_code == 201
        entry = installed.json()
        user.is_admin = False
        asset_url = f"/api/themes/assets/{entry['id']}/{entry['digest']}/theme.css"
        asset = client.get(asset_url)
        assert asset.status_code == 200 and "text/css" in asset.headers["content-type"]
        assert asset.headers["x-content-type-options"] == "nosniff"
        assert "sandbox" in asset.headers["content-security-policy"]
        assert (
            client.patch(f"/api/themes/{entry['id']}", json={"enabled": False}).status_code == 403
        )
        assert client.delete(f"/api/themes/{entry['id']}").status_code == 403
        user.is_admin = True
        assert client.put("/api/themes/default", json={"theme_id": entry["id"]}).status_code == 200
        assert (
            client.patch(f"/api/themes/{entry['id']}", json={"enabled": False}).status_code == 200
        )
        assert client.get(asset_url).status_code == 404
        assert client.delete(f"/api/themes/{entry['id']}").status_code == 204
        assert client.get("/api/themes").json() == {"default_theme": "native", "themes": []}
