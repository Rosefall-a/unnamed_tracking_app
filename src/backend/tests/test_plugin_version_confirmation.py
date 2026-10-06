"""Public version review/consent preserves publisher, grant and lifecycle boundaries."""

import pytest
import test_plugin_install_sources as install_sources
from test_plugin_install_sources import grants, package_bytes, seed_update

from src.plugin_api.manager_state import manager_state

# Register the existing protocol fixture locally, including when its source
# module has already been collected by the full suite.
gate = install_sources.gate


async def candidate_request(
    boundary,
    source,
    package,
    *,
    preview=False,
    confirmed=False,
    installed_version="1.0.0",
    digest=None,
):
    """Use the actual upload, URL and advertised-catalogue transport contracts."""
    target = f"/api/plugins/{boundary.plugin_id}/update"
    if source != "upload":
        boundary.remote["package"] = package
        body = {
            "url": "https://packages.example/download",
            "source_type": "catalogue" if source == "catalogue" else "url",
            "version_change_confirmed": confirmed,
            "expected_installed_version": installed_version,
        }
        if source == "catalogue":
            body["catalogue_url"] = "https://catalogue.example/list.json"
        if digest:
            body["expected_digest"] = digest
        return await boundary.client.post(
            target + ("/preview-url" if preview else "/url"),
            params={"allow_untrusted": "true"},
            json=body,
        )
    data = {"expected_installed_version": installed_version}
    if digest:
        data["expected_digest"] = digest
    return await boundary.client.put(
        target + ("/preview" if preview else ""),
        params={"allow_untrusted": "true", "version_change_confirmed": confirmed},
        data=data,
        files={"file": ("candidate.upt", package, "application/octet-stream")},
    )


@pytest.mark.parametrize("source", ("upload", "url", "catalogue"))
@pytest.mark.parametrize("version, relation", (("1.0.0", "same"), ("0.9.0", "downgrade")))
async def test_non_newer_versions_preview_then_require_explicit_consent(
    gate, source, version, relation
):
    await seed_update(gate, "update", trust="trusted", permissions=("games.read",))
    before = gate.registry.list()[0]
    active_grants = [row.id for row in await grants(gate)]
    package = package_bytes(
        gate.plugin_id, version=version, trust="trusted", key=gate.key, permissions=("games.read",)
    )
    preview = await candidate_request(gate, source, package, preview=True)
    assert preview.status_code == 200, preview.text
    review = preview.json()
    assert review["version_change"] == relation and review["requires_version_confirmation"]
    assert "install" not in gate.events
    refused = await candidate_request(gate, source, package, digest=review["digest"])
    assert refused.status_code == 409, refused.text
    assert "Confirm" in refused.json()["detail"]
    assert gate.registry.list()[0]["version"] == "1.0.0"
    applied = await candidate_request(
        gate, source, package, confirmed=True, digest=review["digest"]
    )
    assert applied.status_code == 200, applied.text
    assert gate.registry.list()[0]["installation_id"] == before["installation_id"]
    assert [row.id for row in await grants(gate)] == active_grants
    record = manager_state().read()["plugins"][gate.plugin_id]
    if relation == "downgrade":
        assert record["version_pin"] == version and record["automatic_updates"] == "disabled"
        repeated = await candidate_request(
            gate,
            source,
            package,
            confirmed=True,
            installed_version=version,
            digest=review["digest"],
        )
        assert repeated.status_code == 200, repeated.text
        record = manager_state().read()["plugins"][gate.plugin_id]
        assert record["version_pin"] == version and record["automatic_updates"] == "disabled"
        assert [row.id for row in await grants(gate)] == active_grants


@pytest.mark.parametrize("source", ("upload", "url", "catalogue"))
async def test_confirmation_cannot_bypass_changed_installation_or_publisher(gate, source):
    await seed_update(gate, "update", trust="trusted", permissions=("games.read",))
    package = package_bytes(gate.plugin_id, version="1.0.0", trust="trusted", key=gate.key)
    changed = await candidate_request(
        gate, source, package, confirmed=True, installed_version="0.9.0"
    )
    assert changed.status_code == 409 and "changed after review" in changed.text
    unverified = package_bytes(gate.plugin_id, version="1.0.0", trust="unsigned")
    rejected = await candidate_request(gate, source, unverified, confirmed=True)
    assert rejected.status_code == 409 and "publisher" in rejected.text
    assert "install" not in gate.events
    assert [row.capability for row in await grants(gate)] == ["games.read"]
