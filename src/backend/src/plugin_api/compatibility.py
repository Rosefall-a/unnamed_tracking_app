"""Limited legacy eligibility and explicit version diagnostics for plugin management."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol
from uuid import UUID

from .base_contracts import (
    PLUGIN_API_CONTRACT_VERSION,
    parse_semver,
    version_satisfies,
)

LEGACY_WARNING = (
    "This plugin was built for the old v1.0 UI. It runs with limited compatibility: "
    "existing backend features, declarative settings and embedded pages are supported, "
    "but new native UI, themes, shortcuts and built-in section placement require a v1.1 update. "
    "Some old pages may look different or have limited features."
)
SHIPPED_LEGACY_PLUGIN_IDS = frozenset(
    json.loads(Path(__file__).with_name("legacy_compatibility.json").read_text(encoding="utf-8"))[
        "shipped_plugin_ids"
    ]
)


class VersionRequirements(Protocol):
    @property
    def api_contract_version(self) -> str: ...
    @property
    def sdk_version_range(self) -> str: ...
    @property
    def application_version_range(self) -> str: ...


@dataclass
class CompatibilityRequirements:
    """Only the version fields exposed by the runtime inventory, without a fabricated manifest."""

    api_contract_version: str
    sdk_version_range: str
    application_version_range: str


def legacy_plugin_allowed(plugin_id: str, installed: Mapping[str, Any] | None = None) -> bool:
    """Allow shipped references or an authoritative existing installation, never an ID prefix."""
    if plugin_id in SHIPPED_LEGACY_PLUGIN_IDS:
        return True
    if not installed or installed.get("plugin_id") != plugin_id:
        return False
    try:
        UUID(str(installed.get("installation_id", "")))
    except ValueError:
        return False
    return True


def is_legacy_contract(version: str) -> bool:
    return parse_semver(version)[:2] == (1, 0)


def plugin_contract_compatibility_reason(
    declared_version: str,
    host_version: str = PLUGIN_API_CONTRACT_VERSION,
    *,
    allow_legacy: bool = False,
) -> str | None:
    """New plugins require v1.1; explicitly eligible old installations use a limited adapter."""
    declared = parse_semver(declared_version)
    host = parse_semver(host_version)
    if host >= (1, 1, 0) and declared[:2] == (1, 0):
        if allow_legacy:
            return None
        return (
            f"Plugin API contract {declared_version} is v1.0-only. "
            "Limited compatibility is available for shipped examples and already-installed plugins. "
            f"New plugins must target a supported v1.1 contract ({host_version})."
        )
    if declared[0] != host[0] or declared > host:
        return f"Plugin API contract {declared_version} is not supported by this host ({host_version})."
    return None


def manifest_compatibility_checks(
    manifest: VersionRequirements,
    sdk_version: str,
    application_version: str,
    *,
    allow_legacy: bool = False,
) -> list[dict[str, str]]:
    """Report every failing requirement; a legacy SDK adapter never bypasses an app range."""
    limited = allow_legacy and is_legacy_contract(manifest.api_contract_version)
    contract_error = plugin_contract_compatibility_reason(
        manifest.api_contract_version, sdk_version, allow_legacy=allow_legacy
    )
    sdk_ok = version_satisfies(sdk_version, manifest.sdk_version_range)
    legacy_sdk = (
        limited
        and parse_semver(sdk_version) >= (1, 1, 0)
        and version_satisfies("1.0.0", manifest.sdk_version_range)
    )
    app_ok = version_satisfies(application_version, manifest.application_version_range)
    return [
        {
            "key": "api_contract",
            "title": "UI/API contract",
            "required": manifest.api_contract_version,
            "host": PLUGIN_API_CONTRACT_VERSION,
            "status": "incompatible" if contract_error else "limited" if limited else "supported",
            "reason": contract_error
            or (
                "Limited v1.0 adapter. Update to v1.1 for native UI, themes and shortcuts."
                if limited
                else "Supported by this host."
            ),
        },
        {
            "key": "sdk",
            "title": "Plugin SDK",
            "required": manifest.sdk_version_range,
            "host": sdk_version,
            "status": "supported" if sdk_ok else "limited" if legacy_sdk else "incompatible",
            "reason": (
                "Supported by this host."
                if sdk_ok
                else "Using the limited v1.0 SDK adapter."
                if legacy_sdk
                else f"Host plugin SDK {sdk_version} is outside this plugin's required "
                f"range ({manifest.sdk_version_range}). Choose a verified compatible plugin release "
                "or update the host and plugin runtime together."
            ),
        },
        {
            "key": "application",
            "title": "Application compatibility",
            "required": manifest.application_version_range,
            "host": application_version,
            "status": "supported" if app_ok else "incompatible",
            "reason": "Supported by this host."
            if app_ok
            else (
                f"Host application compatibility version {application_version} is outside this "
                f"plugin's required range ({manifest.application_version_range}). "
                "Update the application or choose a verified release supporting this host."
            ),
        },
    ]
