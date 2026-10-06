"""Load the reviewed publisher trust policy used for plugin verification."""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from pathlib import Path

from .updates import TrustedPublisher


class PublisherTrustError(ValueError):
    """Raised when the deployed publisher trust policy is malformed."""


_KEY_ID = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_STATUSES = {"active", "retiring", "revoked"}
_DEFAULT_REGISTRY = Path(__file__).with_name("trusted_publishers.json")


def _publisher_metadata(entry: dict) -> tuple[str, str, str, list[str], str]:
    key_id = entry.get("key_id")
    status = entry.get("status")
    encoded_key = entry.get("public_key_b64")
    scopes = entry.get("plugin_id_prefixes")
    digest = entry.get("public_key_sha256")
    error = "publisher trust registry contains invalid publisher metadata"
    if not isinstance(key_id, str) or not _KEY_ID.fullmatch(key_id):
        raise PublisherTrustError(error)
    if not isinstance(status, str) or status not in _STATUSES:
        raise PublisherTrustError(error)
    if not isinstance(encoded_key, str):
        raise PublisherTrustError(error)
    if (
        not isinstance(scopes, list)
        or not scopes
        or not all(isinstance(scope, str) and scope for scope in scopes)
    ):
        raise PublisherTrustError(error)
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise PublisherTrustError(error)
    return key_id, status, encoded_key, scopes, digest


def _legacy_manifest_hashes(value: object) -> dict[str, list[str]]:
    error = "invalid legacy manifest review pins"
    if not isinstance(value, dict) or len(value) > 2048:
        raise PublisherTrustError(error)
    for key, pins in value.items():
        if not isinstance(key, str) or not re.fullmatch(r"[a-f0-9]{64}", key):
            raise PublisherTrustError(error)
        if not isinstance(pins, list) or not pins or len(pins) > 128:
            raise PublisherTrustError(error)
        if any(not isinstance(pin, str) or not re.fullmatch(r"[a-f0-9]{64}", pin) for pin in pins):
            raise PublisherTrustError(error)
    return value


def _load_publisher(entry: object, publishers: dict[str, TrustedPublisher]) -> TrustedPublisher:
    if not isinstance(entry, dict):
        raise PublisherTrustError("publisher trust registry contains an invalid entry")
    key_id, status, encoded_key, scopes, digest = _publisher_metadata(entry)
    if key_id in publishers:
        raise PublisherTrustError("publisher trust registry contains duplicate key identifiers")
    try:
        public_key = base64.b64decode(encoded_key, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise PublisherTrustError(
            "publisher trust registry contains an invalid public key"
        ) from exc
    if len(public_key) != 32 or hashlib.sha256(public_key).hexdigest() != digest:
        raise PublisherTrustError("publisher trust registry public-key digest does not match")
    channel = entry.get("channel", "community")
    if not isinstance(channel, str) or channel not in {"official", "demo", "community"}:
        raise PublisherTrustError("invalid publisher channel")
    legacy = _legacy_manifest_hashes(entry.get("legacy_manifest_hashes", {}))
    return TrustedPublisher(
        key_id=key_id,
        public_key=public_key,
        publisher=str(entry.get("publisher", "")),
        status=status,
        plugin_id_prefixes=tuple(scopes),
        channel=channel,
        legacy_manifest_hashes=legacy,
        require_manifest_binding=True,
    )


def load_trusted_publishers(path: Path | None = None) -> dict[str, TrustedPublisher]:
    """Load a reviewed registry; revoked keys remain visible but are never trusted."""
    registry_path = path or _DEFAULT_REGISTRY
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PublisherTrustError("publisher trust registry cannot be read") from exc
    if (
        not isinstance(data, dict)
        or data.get("schema_version") != 1
        or not isinstance(data.get("publishers"), list)
    ):
        raise PublisherTrustError("publisher trust registry has an unsupported schema")

    publishers: dict[str, TrustedPublisher] = {}
    for entry in data["publishers"]:
        publisher = _load_publisher(entry, publishers)
        publishers[publisher.key_id] = publisher
    if not publishers:
        raise PublisherTrustError("publisher trust registry must contain at least one publisher")
    return publishers


__all__ = ["PublisherTrustError", "load_trusted_publishers"]
