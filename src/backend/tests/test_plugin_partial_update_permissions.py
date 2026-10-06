"""Digest-bound manual update review can decline individual capabilities."""

import io
import json
import zipfile

import pytest
from test_plugin_install_sources import (
    grants,
    package_bytes,
    plugin_gate,  # noqa: F401 - registers "gate"
    seed_update,
)


def _digest(payload):
    """Read the manifest's existing canonical payload digest."""
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        return json.loads(archive.read("manifest.json"))["integrity"]["sha256"]


async def _update(gate, source, payload, consent):
    """Submit the same reviewed decision through each public update source."""
    decision = dict(consent)
    if source == "staged":
        stage = await gate.client.put(
            f"/api/plugins/{gate.plugin_id}/update",
            params={"allow_untrusted": True},
            files={"file": ("candidate.utp", payload)},
        )
        assert stage.json()["status"] == "awaiting_permissions", stage.text
        return await gate.client.post(f"/api/plugins/{gate.plugin_id}/update/staged", json=decision)
    digest = decision.pop("expected_digest", None)
    if source == "url":
        gate.remote["package"] = payload
        return await gate.client.post(
            f"/api/plugins/{gate.plugin_id}/update/url",
            params=decision,
            json={"url": "https://packages.example/download", "expected_digest": digest},
        )
    return await gate.client.put(
        f"/api/plugins/{gate.plugin_id}/update",
        params=decision,
        data={"expected_digest": digest} if digest else {},
        files={"file": ("candidate.utp", payload)},
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ("upload", "url", "staged"))
@pytest.mark.parametrize("reviewed", (False, True))
async def test_update_respects_explicit_partial_review(gate, source, reviewed):
    """A reviewed subset activates; incomplete unattended consent remains staged."""
    await seed_update(gate, "update", permissions=("games.read",))
    installation_id = gate.registry.list()[0]["installation_id"]
    payload = package_bytes(gate.plugin_id, permissions=("games.read", "media.read", "media.write"))
    response = await _update(
        gate,
        source,
        payload,
        {
            "allow_untrusted": True,
            "approved_permissions": ["games.read:v1", "media.read:v1"],
            "permissions_reviewed": reviewed,
            "expected_digest": _digest(payload),
        },
    )
    assert response.status_code == 200, response.text
    active = gate.registry.list()[0]
    assert active["installation_id"] == installation_id
    assert gate.registry.health(gate.plugin_id)
    if reviewed:
        assert response.json()["status"] == "running"
        assert active["version"] == "2.0.0"
        assert {grant.capability for grant in await grants(gate)} == {"games.read", "media.read"}
    else:
        assert response.json()["status"] == "awaiting_permissions"
        assert active["version"] == "1.0.0"
        assert [grant.capability for grant in await grants(gate)] == ["games.read"]
        assert "install" not in gate.events


@pytest.mark.asyncio
@pytest.mark.parametrize("source", ("upload", "url", "staged"))
@pytest.mark.parametrize("digest", (None, "0" * 64))
async def test_partial_review_requires_current_payload_digest(gate, source, digest):
    """An absent or stale snapshot cannot authorize a partial update."""
    await seed_update(gate, "update", permissions=("games.read",))
    payload = package_bytes(gate.plugin_id, permissions=("games.read", "media.write"))
    response = await _update(
        gate,
        source,
        payload,
        {
            "allow_untrusted": True,
            "approved_permissions": ["games.read:v1"],
            "permissions_reviewed": True,
            "expected_digest": digest,
        },
    )
    assert response.status_code == (400 if digest is None else 409), response.text
    assert gate.registry.list()[0]["version"] == "1.0.0"
    assert [grant.capability for grant in await grants(gate)] == ["games.read"]
    assert "install" not in gate.events
