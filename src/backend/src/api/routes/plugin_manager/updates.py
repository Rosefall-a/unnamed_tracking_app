"""Package update review and activation with existing grant compatibility."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.installer import (
    DependencyPlan,
    InspectedPackage,
    InstallationConsent,
    InstallationError,
)
from src.plugin_api.management_auth import get_plugin_manager_admin

from . import acquisition, catalogues, models, runtime

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


_PLUGIN_ADMIN = Depends(get_plugin_manager_admin)
_PLUGIN_UPLOAD = File(...)
_PLUGIN_DB = Depends(get_db)
_APPROVED_PERMISSIONS_QUERY = Query(default=None)
_ADMIN_PASSWORD_FORM = Form(default=None)
_CONFIRM_DANGEROUS_QUERY = Query(default=False)


@router.get("/{plugin_id}/changelog")
async def plugin_changelog(
    plugin_id: str,
    admin: User = _PLUGIN_ADMIN,
) -> dict[str, Any]:
    plugin = next(
        (item for item in await runtime._client.plugins() if item.get("plugin_id") == plugin_id),
        None,
    )
    if plugin is None:
        raise HTTPException(status_code=404, detail="Plugin installation not found.")
    update = await catalogues._check_plugin_update(plugin, admin)
    if update.get("release_notes"):
        return {
            "plugin_id": plugin_id,
            "version": update.get("available_version"),
            "format": "markdown",
            "source": "catalogue",
            "body": update["release_notes"],
        }
    changelog_url = update.get("changelog_url")
    if not isinstance(changelog_url, str):
        return {
            "plugin_id": plugin_id,
            "version": update.get("available_version"),
            "format": "text",
            "source": "none",
            "body": "No release notes were supplied by this update source.",
        }
    path: Path | None = None
    try:
        path, _, _ = await acquisition._download_remote_file(changelog_url, json_document=True)
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=502, detail="Plugin changelog is not UTF-8 text."
            ) from exc
        return {
            "plugin_id": plugin_id,
            "version": update.get("available_version"),
            "format": "markdown",
            "source": "remote",
            "url": changelog_url,
            "body": body,
        }
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


async def _update_context(
    plugin_id: str,
    inspected: InspectedPackage,
    db: AsyncSession,
    operation: str = "update",
) -> tuple[dict[str, Any], UUID, Any, DependencyPlan, bool]:
    try:
        plan = await acquisition._plugin_installer().plan_update(
            plugin_id, inspected, db, operation=operation
        )
    except InstallationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    assert plan.installed is not None
    return (
        plan.installed,
        plan.installation_id,
        plan.permissions,
        plan.dependencies,
        plan.can_retain_grants,
    )


def _update_preview(
    inspected: InspectedPackage,
    installed: dict[str, Any],
    permission_delta: Any,
    dependencies: DependencyPlan,
    *,
    can_retain_grants: bool,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    preview = acquisition._install_preview(
        inspected,
        dependencies,
        source=(
            source
            if source is not None
            else installed.get("source")
            if isinstance(installed.get("source"), dict)
            else None
        ),
    )
    new_keys = {
        acquisition._permission_key(item.name.value, item.version)
        for item in permission_delta.newly_requested_grants
    }
    preview["permissions"] = [
        {**permission, "new": permission["key"] in new_keys}
        for permission in preview["permissions"]
    ]
    preview.update(
        {
            "operation": "update",
            "installed_version": installed.get("version"),
            "permission_delta": permission_delta.model_dump(mode="json"),
            "new_permission_keys": sorted(new_keys),
            "existing_grants_retained": can_retain_grants,
            "identity_warning": (
                None
                if can_retain_grants
                else (
                    "Unverified updates cannot inherit existing permission grants; "
                    "review every requested permission again."
                )
            ),
            "release_notes": (
                inspected.package.distribution.get("release_notes")
                or (
                    source.get("release_notes")
                    if isinstance(source, dict)
                    else installed.get("source", {}).get("release_notes")
                    if isinstance(installed.get("source"), dict)
                    else None
                )
            ),
        }
    )
    return preview


@router.put("/{plugin_id}/update/preview")
async def preview_plugin_update(
    plugin_id: str,
    file: UploadFile = _PLUGIN_UPLOAD,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
) -> dict[str, Any]:
    del admin
    temporary_path: Path | None = None
    try:
        temporary_path, _, _ = await acquisition._store_plugin_upload(
            file, "plugin-update-preview-"
        )
        inspected = acquisition._inspect_install_candidate(temporary_path)
        installed, _, permission_delta, dependencies, can_retain_grants = await _update_context(
            plugin_id, inspected, db, operation=operation
        )
        return _update_preview(
            inspected,
            installed,
            permission_delta,
            dependencies,
            can_retain_grants=can_retain_grants,
        )
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await file.close()


@router.post("/{plugin_id}/update/preview-url")
async def preview_plugin_update_url(
    plugin_id: str,
    request: models.PluginInstallUrl,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
) -> dict[str, Any]:
    temporary_path: Path | None = None
    try:
        temporary_path, filename, total = await acquisition._download_remote_file(request.url)
        inspected = acquisition._inspect_install_candidate(temporary_path)
        await acquisition._validate_catalogue_candidate(temporary_path, inspected, request, admin)
        installed, _, permission_delta, dependencies, can_retain_grants = await _update_context(
            plugin_id,
            inspected,
            db,
            operation=operation,
        )
        source = {
            "type": request.source_type,
            "url": request.url,
            "catalogue_url": request.catalogue_url,
            "release_notes": request.release_notes,
            "changelog_url": request.changelog_url,
        }
        return {
            **_update_preview(
                inspected,
                installed,
                permission_delta,
                dependencies,
                can_retain_grants=can_retain_grants,
                source=source,
            ),
            "source_url": request.url,
            "download_filename": filename,
            "download_bytes": total,
        }
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.post("/{plugin_id}/update/url")
async def update_plugin_url(
    plugin_id: str,
    request: models.PluginInstallUrl,
    allow_untrusted: bool = False,
    approved_permissions: list[str] | None = _APPROVED_PERMISSIONS_QUERY,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
    permissions_reviewed: bool = False,
) -> dict[str, Any]:
    """Apply inspected remote bytes with the administrator's selected permissions."""
    temporary_path: Path | None = None
    upload: UploadFile | None = None
    try:
        temporary_path, filename, _ = await acquisition._download_remote_file(request.url)
        inspected = acquisition._inspect_install_candidate(temporary_path)
        await acquisition._validate_catalogue_candidate(temporary_path, inspected, request, admin)
        upload = UploadFile(temporary_path.open("rb"), filename=filename)
        return await _update_plugin_package(
            plugin_id,
            upload,
            operation=operation,
            allow_untrusted=allow_untrusted,
            approved_permissions=approved_permissions,
            admin_password=request.admin_password,
            confirm_dangerous=request.confirm_dangerous,
            expected_digest=request.expected_digest,
            permissions_reviewed=permissions_reviewed,
            source_metadata={
                "type": request.source_type,
                "url": request.url,
                "catalogue_url": request.catalogue_url,
                "release_notes": request.release_notes,
                "changelog_url": request.changelog_url,
            },
            admin=admin,
            db=db,
        )
    finally:
        if upload is not None:
            await upload.close()
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


@router.put("/{plugin_id}/update", status_code=200)
async def update_plugin(
    plugin_id: str,
    file: UploadFile = _PLUGIN_UPLOAD,
    allow_untrusted: bool = False,
    approved_permissions: list[str] | None = _APPROVED_PERMISSIONS_QUERY,
    admin_password: str | None = _ADMIN_PASSWORD_FORM,
    confirm_dangerous: bool = _CONFIRM_DANGEROUS_QUERY,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
    permissions_reviewed: bool = False,
    expected_digest: str | None = Form(default=None, min_length=64, max_length=64),
) -> dict[str, Any]:
    """Activate a digest-bound reviewed upload or stage pending permission decisions."""
    return await _update_plugin_package(
        plugin_id,
        file,
        operation=operation,
        allow_untrusted=allow_untrusted,
        approved_permissions=approved_permissions,
        admin_password=admin_password,
        confirm_dangerous=confirm_dangerous,
        permissions_reviewed=permissions_reviewed,
        expected_digest=expected_digest if isinstance(expected_digest, str) else None,
        source_metadata=None,
        admin=admin,
        db=db,
    )


async def _update_plugin_package(
    plugin_id: str,
    file: UploadFile,
    *,
    allow_untrusted: bool,
    approved_permissions: list[str] | None,
    admin_password: str | None,
    confirm_dangerous: bool,
    source_metadata: dict[str, Any] | None,
    admin: User,
    db: AsyncSession,
    expected_digest: str | None = None,
    operation: str = "update",
    permissions_reviewed: bool = False,
) -> dict[str, Any]:
    return await acquisition._commit_plugin_upload(
        file,
        consent=InstallationConsent(
            allow_untrusted=allow_untrusted,
            approved_permissions=tuple(approved_permissions)
            if isinstance(approved_permissions, list)
            else (),
            admin_password=admin_password,
            confirm_dangerous=confirm_dangerous,
            expected_digest=expected_digest,
            permissions_reviewed=permissions_reviewed,
        ),
        source_metadata=source_metadata,
        admin=admin,
        db=db,
        plugin_id=plugin_id,
        operation=operation,
    )
