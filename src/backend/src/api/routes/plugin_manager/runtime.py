"""Live installations, capabilities and the shared isolated-runtime client."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator
from uuid import UUID

from fastapi import Depends, HTTPException, Response
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.plugin_permissions import PluginPermissionGrant
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.compatibility import (
    CompatibilityRequirements,
    legacy_plugin_allowed,
    manifest_compatibility_checks,
)
from src.plugin_api.contracts import PLUGIN_API_CONTRACT_VERSION
from src.plugin_api.grants import installation_is_executable
from src.plugin_api.management_auth import get_plugin_manager_admin
from src.plugin_api.manager_state import manager_state
from src.plugin_api.runtime_client import (
    PluginRuntimeClient,
    PluginRuntimeRequestError,
    PluginRuntimeUnavailable,
)

_client = PluginRuntimeClient()


_PLUGIN_DB = Depends(get_db)


_PLUGIN_ADMIN = Depends(get_plugin_manager_admin)


def _private_plugin_response(response: Response) -> None:
    """Plugin user data must not be cached or interpreted through MIME sniffing."""
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"


def _runtime_error(exc: PluginRuntimeUnavailable) -> HTTPException:
    return HTTPException(status_code=503, detail=str(exc))


def _runtime_request_error(exc: PluginRuntimeRequestError) -> HTTPException:
    return HTTPException(status_code=422, detail=str(exc))


@contextmanager
def _runtime_errors() -> Iterator[None]:
    """Preserve runtime policy and connection errors as actionable JSON responses."""
    try:
        yield
    except PluginRuntimeRequestError as exc:
        raise _runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise _runtime_error(exc) from exc


async def _installed_plugins() -> list[dict[str, Any]]:
    store = manager_state()
    try:
        inventory = store.reconcile(await _client.plugins())
    except (PluginRuntimeRequestError, PluginRuntimeUnavailable) as exc:
        inventory = [
            {
                **item,
                "runtime_available": False,
                "status": "unknown",
                "health": "unknown",
                "runtime_error": str(exc),
                "runtime": {
                    **item.get("runtime", {}),
                    "available": False,
                    "mechanism": "unavailable",
                    "sandbox_available": False,
                    "bubblewrap_available": None,
                    "last_error": str(exc),
                },
            }
            for item in store.read()["plugins"].values()
        ]
    for item in inventory:
        # The runtime reports checked package metadata. Missing historical ranges are
        # reported as unknown rather than invented; acquisition always has a full manifest.
        if item.get("sdk_version_range") and item.get("application_version_range"):
            manifest = CompatibilityRequirements(
                api_contract_version=item.get("api_contract_version", "1.0.0"),
                sdk_version_range=item["sdk_version_range"],
                application_version_range=item["application_version_range"],
            )
            try:
                item["compatibility_checks"] = manifest_compatibility_checks(
                    manifest,
                    os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
                    os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
                    allow_legacy=legacy_plugin_allowed(item["plugin_id"], item),
                )
            except ValueError:
                # One damaged historical installation must not prevent the
                # manager from displaying the rest of the server inventory.
                item.update(
                    compatible=False,
                    compatibility_reason="Plugin version metadata is invalid. Choose a verified compatible release.",
                )
    return [
        {
            **item,
            "host_api_contract_version": PLUGIN_API_CONTRACT_VERSION,
            "host_sdk_version": os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
            "host_application_version": os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
        }
        for item in inventory
    ]


async def _live_plugin(plugin_id: str, *, require_enabled: bool = True) -> dict[str, Any]:
    """Resolve a live installation before any capability can execute."""
    with _runtime_errors():
        installed = await _client.plugins()
    matches = [item for item in installed if item.get("plugin_id") == plugin_id]
    if len(matches) != 1 or not matches[0].get("installation_id"):
        raise HTTPException(status_code=404, detail="Plugin installation not found.")
    plugin = matches[0]
    try:
        UUID(str(plugin["installation_id"]))
    except ValueError as exc:
        raise HTTPException(
            status_code=409, detail="Plugin installation identity is invalid."
        ) from exc
    if require_enabled and not installation_is_executable(plugin):
        raise HTTPException(status_code=409, detail="Plugin installation is not executable.")
    return plugin


async def _plugin_and_capabilities(
    plugin_id: str,
    db: AsyncSession,
    user: User,
    *,
    require_enabled: bool = True,
) -> tuple[dict[str, Any], frozenset[str]]:
    """Resolve one enabled installation and this user's effective grants."""
    plugin = await _live_plugin(plugin_id, require_enabled=require_enabled)
    if not installation_is_executable(plugin):
        return plugin, frozenset()
    installation_id = UUID(str(plugin["installation_id"]))
    rows = await db.execute(
        select(
            PluginPermissionGrant.capability,
            PluginPermissionGrant.capability_version,
        ).where(
            PluginPermissionGrant.plugin_id == plugin_id,
            PluginPermissionGrant.installation_id == installation_id,
            PluginPermissionGrant.revoked_at.is_(None),
            PluginPermissionGrant.device_id.is_(None),
            or_(
                PluginPermissionGrant.user_id.is_(None),
                PluginPermissionGrant.user_id == user.id,
            ),
        )
    )
    granted = [str(capability) for capability, version in rows if version == 1]
    from src.plugin_api.grants import effective_capabilities

    capabilities = await effective_capabilities(db, plugin_id, installation_id, user.id, granted)
    if plugin.get("legacy_compatibility") is True:
        capabilities = frozenset(
            item
            for item in capabilities
            if item
            not in {
                "frontend.native",
                "frontend.themes",
                "frontend.home.widgets",
                "frontend.shortcuts",
                "frontend.placement.sidebar",
                "frontend.placement.settings.admin",
                "frontend.placement.settings.account",
                "frontend.placement.settings.preferences",
            }
        )
    return plugin, capabilities
