"""Plugin Manager policy, execution, permission and package lifecycle endpoints."""

from __future__ import annotations

import asyncio
import hashlib
import io
import logging
import secrets
import time
import zipfile
from typing import Any
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, or_, select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.auth import get_current_admin, hash_token
from src.database.models.auth import UserApiKey
from src.database.models.plugin_notification_provider import PluginNotificationProviderRegistration
from src.database.models.plugin_permission_audit import PluginPermissionAudit
from src.database.models.plugin_permissions import (
    PluginClientIdentity,
    PluginPermissionGrant,
    PluginPermissionRequest,
)
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.contracts import PermissionDeclaration
from src.plugin_api.grants import installation_is_executable
from src.plugin_api.installer import InstallationConsent, InstallationError, plan_dependencies
from src.plugin_api.lifecycle import plugin_contract_active
from src.plugin_api.management_auth import (
    MANAGEMENT_PREFIX,
    MANAGEMENT_SCOPES,
    get_plugin_manager_admin,
    get_plugin_manager_reader,
)
from src.plugin_api.manager_state import manager_state
from src.plugin_api.package_metadata import package_readme
from src.plugin_api.runtime_client import PluginRuntimeRequestError, PluginRuntimeUnavailable

from . import acquisition, catalogues, models, runtime, updates

router = APIRouter(prefix="/api/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)


@router.get("/{plugin_id}/details")
async def plugin_details(
    plugin_id: str, response: Response, admin: User = Depends(get_plugin_manager_reader)
) -> dict[str, Any]:
    """Display the installed release's documentation, including disabled packages."""
    del admin
    runtime._private_plugin_response(response)
    await runtime._live_plugin(plugin_id, require_enabled=False)
    try:
        package = await runtime._client.package_archive(plugin_id)
        with zipfile.ZipFile(io.BytesIO(package)) as archive:
            return {"readme": package_readme(archive)}
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    except (PluginRuntimeRequestError, ValueError, zipfile.BadZipFile) as exc:
        raise HTTPException(422, "Installed plugin documentation is unavailable.") from exc


@router.get("/manager-settings")
async def get_manager_settings(admin: User = Depends(get_plugin_manager_admin)) -> dict:
    del admin
    return manager_state().settings()


@router.put("/manager-settings")
async def save_manager_settings(
    payload: models.ManagerSettingsIn, admin: User = Depends(get_plugin_manager_admin)
) -> dict:
    del admin
    settings = manager_state().settings(payload.model_dump(exclude_none=True))
    try:
        for plugin in await runtime._client.plugins():
            await runtime._client.prune_history(plugin["plugin_id"], settings["retained_versions"])
    except (PluginRuntimeUnavailable, PluginRuntimeRequestError):
        # Host settings remain editable during a runtime outage. Keep package
        # history intact; later package operations apply the saved retention.
        return {**settings, "history_pruning_deferred": True}
    return {**settings, "history_pruning_deferred": False}


@router.put("/{plugin_id}/auto-update")
async def set_plugin_auto_update(
    plugin_id: str, payload: models.AutoUpdateIn, admin: User = Depends(get_plugin_manager_admin)
) -> dict:
    del admin
    if plugin_id not in manager_state().read()["plugins"]:
        raise HTTPException(404, "Plugin installation not found.")
    changes: dict[str, Any] = {"automatic_updates": payload.mode}
    if payload.mode != "disabled":
        changes["version_pin"] = None
    return manager_state().patch(plugin_id, **changes)


@router.post("/{plugin_id}/update/staged/preview")
async def preview_staged_update(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    del admin
    path = manager_state().stage_path(plugin_id)
    if not path.is_file():
        raise HTTPException(404, "No staged package.")
    inspected = acquisition._inspect_install_candidate(path)
    installed, _, delta, dependencies, retain = await updates._update_context(
        plugin_id, inspected, db
    )
    return updates._update_preview(
        inspected, installed, delta, dependencies, can_retain_grants=retain
    )


@router.post("/{plugin_id}/update/staged")
async def activate_staged_update(
    plugin_id: str,
    payload: models.PackageOperationIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    path = manager_state().stage_path(plugin_id)
    if not path.is_file():
        raise HTTPException(404, "No staged package.")
    record = manager_state().read()["plugins"].get(plugin_id, {})
    if payload.expected_digest:
        inspected = acquisition._inspect_install_candidate(path)
        if inspected.package.manifest.integrity.sha256 != payload.expected_digest:
            raise HTTPException(409, "Staged package changed; review its permissions again.")
    if payload.confirmed and not payload.approved_permissions:
        manager_state().patch(
            plugin_id, staged_update={**record.get("staged_update", {}), "status": "denied"}
        )
        return {"plugin_id": plugin_id, "status": "denied"}
    return await _perform_package_operation(
        plugin_id,
        path.read_bytes(),
        payload,
        admin,
        db,
        source=record.get("staged_update", {}).get("source"),
    )


async def _perform_package_operation(
    plugin_id: str,
    package: bytes,
    payload: models.PackageOperationIn,
    admin: User,
    db: AsyncSession,
    *,
    operation: str = "update",
    source: dict | None = None,
) -> dict:
    try:
        return await acquisition._plugin_installer().install(
            package,
            consent=InstallationConsent(
                approved_permissions=tuple(payload.approved_permissions),
                expected_digest=payload.expected_digest,
                allow_untrusted=payload.allow_untrusted,
                confirm_dangerous=payload.confirm_dangerous,
                admin_password=payload.admin_password,
            ),
            admin=admin,
            db=db,
            update_plugin_id=plugin_id,
            operation=operation,
            source=source,
        )
    except InstallationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@router.post("/{plugin_id}/reinstall")
async def reinstall_plugin(
    plugin_id: str,
    payload: models.PackageOperationIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    if payload.purge and not payload.confirmed:
        raise HTTPException(409, "Reinstall with purge requires explicit destructive confirmation.")
    package = await runtime._client.package_archive(plugin_id)
    if payload.purge:
        await runtime._client.purge_data(plugin_id)
        await _purge_plugin_database(db, plugin_id)
        await db.commit()
    return await _perform_package_operation(
        plugin_id, package, payload, admin, db, operation="reinstall"
    )


@router.post("/{plugin_id}/rollback")
async def rollback_plugin(
    plugin_id: str,
    payload: models.PackageOperationIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    plugin = next(
        (item for item in await runtime._client.plugins() if item["plugin_id"] == plugin_id), None
    )
    history = plugin.get("history", []) if plugin else []
    history_id = (
        str(payload.history_id) if payload.history_id else history[0]["id"] if history else None
    )
    if history_id is None:
        raise HTTPException(409, "No retained package version.")
    package = await runtime._client.package_archive(plugin_id, history_id)
    return await _perform_package_operation(
        plugin_id, package, payload, admin, db, operation="rollback"
    )


@router.delete("/{plugin_id}/history/{history_id}")
async def delete_package_history(
    plugin_id: str, history_id: UUID, admin: User = Depends(get_plugin_manager_admin)
) -> dict:
    del admin
    await runtime._client.prune_history(
        plugin_id, manager_state().settings()["retained_versions"], str(history_id)
    )
    manager_state().reconcile(await runtime._client.plugins())
    return {"deleted": True}


@router.post("/{plugin_id}/stop")
async def stop_plugin(plugin_id: str, admin: User = Depends(get_plugin_manager_admin)) -> dict:
    del admin
    await runtime._client.stop_runtime(quote(plugin_id, safe=""))
    manager_state().reconcile(await runtime._client.plugins())
    return {"plugin_id": plugin_id, "status": "stopped"}


@router.post("/{plugin_id}/start")
async def start_plugin(plugin_id: str, admin: User = Depends(get_plugin_manager_admin)) -> dict:
    plugin = next(
        (item for item in await runtime._client.plugins() if item["plugin_id"] == plugin_id), None
    )
    if not plugin or not plugin.get("enabled"):
        raise HTTPException(409, "Enable this plugin before starting it.")
    if not plugin_contract_active(plugin):
        raise HTTPException(409, "This plugin requires a verified v1.1.0 update before it can run.")
    await runtime._client.start(quote(plugin_id, safe=""), user_id=str(admin.id))
    manager_state().reconcile(await runtime._client.plugins())
    return {"plugin_id": plugin_id, "status": "running"}


@router.post("/management/tokens", status_code=201)
async def create_management_token(
    payload: models.ManagementTokenIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin),
) -> dict:
    if not payload.scopes or not set(payload.scopes).issubset(MANAGEMENT_SCOPES):
        raise HTTPException(422, "Choose only plugin management scopes.")
    token = MANAGEMENT_PREFIX + secrets.token_urlsafe(32)
    row = UserApiKey(
        user_id=admin.id,
        name=payload.name,
        key_prefix=token[:12],
        key_hash=hash_token(token),
        scopes=sorted(set(payload.scopes)),
    )
    db.add(row)
    await db.commit()
    return {"id": str(row.id), "token": token, "scopes": row.scopes}


@router.delete("/management/tokens/{token_id}")
async def revoke_management_token(
    token_id: UUID, db: AsyncSession = Depends(get_db), admin: User = Depends(get_current_admin)
) -> dict:
    del admin
    row = await db.scalar(
        select(UserApiKey).where(
            UserApiKey.id == token_id, UserApiKey.key_prefix.startswith(MANAGEMENT_PREFIX)
        )
    )
    if row is None:
        raise HTTPException(404, "Plugin management token not found.")
    row.revoked_at = int(time.time())
    await db.commit()
    return {"revoked": True}


async def _purge_plugin_database(db: AsyncSession, plugin_id: str) -> None:
    from src.database.models.media_provider import MediaProviderLink
    from src.database.models.plugin_permissions import PluginLifecycleTransaction

    for model in (
        MediaProviderLink,
        PluginLifecycleTransaction,
        PluginPermissionGrant,
        PluginPermissionRequest,
        PluginClientIdentity,
        PluginNotificationProviderRegistration,
    ):
        await db.execute(delete(model).where(model.plugin_id == plugin_id))


async def run_automatic_plugin_updates(db: AsyncSession, admin: User) -> dict[str, int]:
    """Discover, validate and stage releases, then apply policy without granting scopes."""
    counts = {"checked": 0, "installed": 0, "staged": 0, "failed": 0}
    store = manager_state()
    for plugin in await runtime._installed_plugins():
        source = plugin.get("source", {})
        if source.get("type") != "catalogue":
            continue
        configured = next(
            (
                item
                for item in catalogues._catalogue_store().list()
                if item["url"] == source.get("catalogue_url") and item["enabled"]
            ),
            None,
        )
        if configured is None:
            continue
        counts["checked"] += 1
        path = None
        try:
            update = await catalogues._check_plugin_update(plugin, admin)
            store.patch(plugin["plugin_id"], available_update=update)
            if not update.get("update_available"):
                continue
            await catalogues._notify_plugin_update(db, update)
            path, _, _ = await acquisition._download_remote_file(update["url"])
            if (
                update.get("package_sha256")
                and hashlib.sha256(path.read_bytes()).hexdigest()
                != update["package_sha256"].lower()
            ):
                raise ValueError("Catalogue archive hash differs.")
            inspected = acquisition._inspect_install_candidate(path)
            manifest = inspected.package.manifest
            if (
                manifest.plugin_id != plugin["plugin_id"]
                or manifest.version != update["available_version"]
            ):
                raise ValueError("Catalogue release and package identity differ.")
            if update.get("digest") and update["digest"] != manifest.integrity.sha256:
                raise ValueError("Catalogue package digest differs.")
            plan = await acquisition._plugin_installer().plan_update(
                plugin["plugin_id"], inspected, db
            )
            mode = plugin.get("automatic_updates", "follow")
            enabled = (
                mode == "enabled" or mode == "follow" and store.settings()["automatic_updates"]
            )
            eligible = (
                enabled
                and not plugin.get("version_pin")
                and update["automatic_update"]
                and manifest.automatic_update
                and inspected.package.distribution.get("automatic_update", True)
                and inspected.trust.is_verified
                and plan.dependencies.ready
                and not plan.permissions.newly_requested_grants
            )
            previous_stage = store.read()["plugins"][plugin["plugin_id"]].get("staged_update") or {}
            denied = (
                previous_stage.get("status") == "denied"
                and previous_stage.get("digest") == manifest.integrity.sha256
                and (previous_stage.get("version") or previous_stage.get("available_version"))
                == manifest.version
            )
            eligible = eligible and not denied
            stage = {
                **update,
                "digest": manifest.integrity.sha256,
                "status": "denied"
                if denied
                else (
                    "awaiting_permissions"
                    if plan.permissions.newly_requested_grants
                    else "downloaded"
                ),
            }
            store.stage(plugin["plugin_id"], path.read_bytes(), stage)
            counts["staged"] += 1
            if eligible:
                result = await acquisition._plugin_installer().install(
                    path.read_bytes(),
                    consent=InstallationConsent(),
                    admin=admin,
                    db=db,
                    update_plugin_id=plugin["plugin_id"],
                    source=source,
                )
                if result["status"] == "rolled_back":
                    counts["failed"] += 1
                    await catalogues._notify_plugin_update(db, update, failed=True)
                else:
                    counts["installed"] += 1
        except Exception as exc:
            await db.rollback()
            counts["failed"] += 1
            store.patch(plugin["plugin_id"], last_update_error=str(exc))
            logger.warning(
                "Plugin automatic update failed: plugin_id=%s error=%s", plugin["plugin_id"], exc
            )
            failure = store.read()["plugins"][plugin["plugin_id"]].get("available_update")
            if failure and failure.get("update_available"):
                await catalogues._notify_plugin_update(db, failure, failed=True)
        finally:
            if path is not None:
                path.unlink(missing_ok=True)
    await db.commit()
    return counts


@router.post("/{plugin_id}/permissions/grant")
async def grant_plugin_permissions(
    plugin_id: str,
    payload: models.PackageOperationIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    """Explicitly re-grant declared permissions without replacing package or data."""
    from src.plugin_api.capabilities import calculate_permission_delta
    from src.plugin_api.installer import InstallationPlan

    inspected = await asyncio.to_thread(
        acquisition._plugin_installer()._inspect_snapshot,
        await runtime._client.package_archive(plugin_id),
    )
    manifest = inspected.package.manifest
    requested = set(payload.approved_permissions)
    if payload.expected_digest and manifest.integrity.sha256 != payload.expected_digest:
        raise HTTPException(409, "Active package changed; review its permissions again.")
    refs = tuple(
        p.capability
        for p in manifest.permissions
        if acquisition._permission_key(p.capability.name.value, p.capability.version) in requested
    )
    if len(refs) != len(requested):
        raise HTTPException(422, "Grant only permissions declared by the active package.")
    plugin = next(
        item for item in await runtime._client.plugins() if item["plugin_id"] == plugin_id
    )
    installation_id = UUID(plugin["installation_id"])
    plan = InstallationPlan(
        inspected,
        installation_id,
        plan_dependencies(manifest, await runtime._client.plugins()),
        calculate_permission_delta((), refs, ()),
    )
    try:
        acquisition._plugin_installer().confirm(
            plan,
            InstallationConsent(
                allow_untrusted=payload.allow_untrusted,
                approved_permissions=tuple(requested),
                confirm_dangerous=payload.confirm_dangerous,
                admin_password=payload.admin_password,
            ),
            admin,
        )
    except InstallationError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc
    for ref in refs:
        db.add(
            PluginPermissionGrant(
                plugin_id=plugin_id,
                installation_id=installation_id,
                capability=ref.name.value,
                capability_version=ref.version,
            )
        )
        db.add(
            PluginPermissionAudit(
                plugin_id=plugin_id,
                installation_id=installation_id,
                capability=ref.name.value,
                capability_version=ref.version,
                user_id=admin.id,
                decision="allowed",
                reason="administrator explicit permission re-grant",
            )
        )
    await db.commit()
    return {"granted": sorted(requested)}


@router.post("/{plugin_id}/permissions/preview")
async def preview_plugin_permissions(
    plugin_id: str, admin: User = Depends(get_plugin_manager_admin)
) -> dict:
    del admin
    inspected = await asyncio.to_thread(
        acquisition._plugin_installer()._inspect_snapshot,
        await runtime._client.package_archive(plugin_id),
    )
    return acquisition._install_preview(inspected)


@router.get("", response_model=list[dict])
async def list_plugins(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_plugin_manager_reader),
) -> list[dict]:
    from src.plugin_api.grants import effective_capabilities

    plugins = await runtime._installed_plugins()
    result: list[dict] = []
    for plugin in plugins:
        granted: list[str] = []
        installation_id = plugin.get("installation_id")
        if installation_id:
            rows = await db.execute(
                select(
                    PluginPermissionGrant.capability,
                    PluginPermissionGrant.capability_version,
                ).where(
                    PluginPermissionGrant.plugin_id == plugin.get("plugin_id"),
                    PluginPermissionGrant.installation_id == UUID(str(installation_id)),
                    PluginPermissionGrant.revoked_at.is_(None),
                    PluginPermissionGrant.device_id.is_(None),
                    or_(
                        PluginPermissionGrant.user_id.is_(None),
                        PluginPermissionGrant.user_id == user.id,
                    ),
                )
            )
            granted = [str(capability) for capability, version in rows if version == 1]
        result.append(
            {
                **plugin,
                "permission_details": [
                    acquisition._permission_preview(PermissionDeclaration.model_validate(item))
                    for item in plugin.get("permission_declarations", [])
                ],
                "granted_capabilities": sorted(set(granted)),
                "effective_capabilities": (
                    sorted(
                        await effective_capabilities(
                            db,
                            str(plugin["plugin_id"]),
                            UUID(str(installation_id)),
                            user.id,
                            granted,
                        )
                    )
                    if installation_id and installation_is_executable(plugin)
                    else []
                ),
            }
        )
    return sorted(result, key=lambda value: value["plugin_id"])


@router.delete("/{plugin_id}", status_code=204)
async def delete_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> Response:
    del admin
    try:
        await runtime._client.delete(quote(plugin_id, safe=""))
    except PluginRuntimeRequestError as exc:
        raise runtime._runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    await _purge_plugin_database(db, plugin_id)
    await db.commit()
    manager_state().remove(plugin_id)
    return Response(status_code=204)


@router.post("/{plugin_id}/enable")
async def enable_plugin(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    plugin = next(
        (item for item in await runtime._client.plugins() if item.get("plugin_id") == plugin_id),
        None,
    )
    if plugin is None or not plugin.get("installation_id"):
        raise HTTPException(status_code=404, detail="Plugin installation not found.")
    if not plugin_contract_active(plugin):
        raise HTTPException(
            status_code=409,
            detail="This plugin requires a verified v1.1.0 update before it can run.",
        )
    installation_id = UUID(str(plugin["installation_id"]))
    pending = await db.scalar(
        select(PluginPermissionRequest.id).where(
            PluginPermissionRequest.plugin_id == plugin_id,
            PluginPermissionRequest.installation_id == installation_id,
            PluginPermissionRequest.status == "pending",
        )
    )
    if pending is not None:
        raise HTTPException(
            status_code=403,
            detail="Approve all pending plugin permissions before enabling this plugin.",
        )
    try:
        await runtime._client.start(quote(plugin_id, safe=""), user_id=str(admin.id))
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    return {"plugin_id": plugin_id, "enabled": True}


@router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, admin: User = Depends(get_plugin_manager_admin)) -> dict:
    del admin
    try:
        await runtime._client.stop(quote(plugin_id, safe=""))
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    return {"plugin_id": plugin_id, "enabled": False}


@router.post("/{plugin_id}/retry")
async def retry_plugin(plugin_id: str, admin: User = Depends(get_plugin_manager_admin)) -> dict:
    del admin
    plugin = await runtime._live_plugin(plugin_id, require_enabled=False)
    if not plugin_contract_active(plugin):
        raise HTTPException(409, "This plugin requires a verified v1.1.0 update before it can run.")
    encoded = quote(plugin_id, safe="")
    try:
        await runtime._client.stop(encoded)
    except PluginRuntimeUnavailable:
        pass
    try:
        await runtime._client.start(encoded)
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    return {"plugin_id": plugin_id, "status": "running"}


@router.post("/{plugin_id}/permissions/revoke")
async def revoke_plugin_permissions(
    plugin_id: str,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict:
    del admin
    rows = await db.scalars(
        select(PluginPermissionGrant).where(
            PluginPermissionGrant.plugin_id == plugin_id,
            PluginPermissionGrant.revoked_at.is_(None),
        )
    )
    count = 0
    for row in rows:
        row.revoked_at = int(time.time())
        count += 1
    await db.execute(
        sql_update(PluginNotificationProviderRegistration)
        .where(
            PluginNotificationProviderRegistration.plugin_id == plugin_id,
            PluginNotificationProviderRegistration.revoked_at.is_(None),
        )
        .values(revoked_at=int(time.time()))
    )
    await db.commit()
    return {"plugin_id": plugin_id, "status": "revoked", "count": count}


@router.get("/{plugin_id}/logs")
async def plugin_logs(
    plugin_id: str,
    level: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict[str, Any]:
    del admin
    if level is not None and level not in {"debug", "info", "warning", "error"}:
        raise HTTPException(status_code=400, detail="Unknown diagnostic level.")
    try:
        diagnostics = await runtime._client.logs(quote(plugin_id, safe=""))
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    events = diagnostics.get("events", [])
    if not isinstance(events, list):
        events = []
    events = [event for event in events if isinstance(event, dict)]
    if level is not None:
        events = [event for event in events if event.get("level") == level]
    diagnostics["events"] = events[-limit:]
    return diagnostics
