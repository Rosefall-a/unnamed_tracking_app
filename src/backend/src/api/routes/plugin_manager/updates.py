"""Package update review and activation with existing grant compatibility."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.contracts import parse_semver
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
_PLUGIN_DB = Depends(get_db)
_PACKAGE_UPLOAD = File(...)
_APPROVED_PERMISSIONS = Query(default=None)
_CONFIRM_DANGEROUS = Query(default=False)


@router.get("/{plugin_id}/changelog")
async def plugin_changelog(
    plugin_id: str,
    admin: User = _PLUGIN_ADMIN,
) -> dict[str, Any]:
    """Return catalogue notes or a bounded UTF-8 changelog for the selected release."""
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
            plugin_id, inspected, db, operation=operation, allow_non_newer=True
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
    candidate_version = parse_semver(inspected.package.manifest.version)
    current_version = parse_semver(str(installed.get("version", "0.0.0")))
    version_change = (
        "downgrade"
        if candidate_version < current_version
        else "same"
        if candidate_version == current_version
        else "upgrade"
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
            "version_change": version_change,
            "requires_version_confirmation": version_change != "upgrade",
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
    file: UploadFile = _PACKAGE_UPLOAD,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
) -> dict[str, Any]:
    """Inspect an upload without activating it, including same-version and older releases."""
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
    """Inspect a bounded remote package and report its version/permission changes."""
    temporary_path: Path | None = None
    try:
        temporary_path, filename, total = await acquisition._download_remote_file(request.url)
        inspected = acquisition._inspect_install_candidate(temporary_path)
        entries = await acquisition._validate_catalogue_candidate(
            temporary_path, inspected, request, admin
        )
        installed, _, permission_delta, dependencies, can_retain_grants = await _update_context(
            plugin_id,
            inspected,
            db,
            operation=operation,
        )
        source = acquisition._acquisition_source(request, inspected, entries)
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
    approved_permissions: list[str] | None = _APPROVED_PERMISSIONS,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
) -> dict[str, Any]:
    """Apply the reviewed remote bytes with explicit consent for non-newer versions."""
    temporary_path: Path | None = None
    upload: UploadFile | None = None
    try:
        temporary_path, filename, _ = await acquisition._download_remote_file(request.url)
        inspected = acquisition._inspect_install_candidate(temporary_path)
        entries = await acquisition._validate_catalogue_candidate(
            temporary_path, inspected, request, admin
        )
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
            version_change_confirmed=request.version_change_confirmed,
            expected_installed_version=request.expected_installed_version,
            source_metadata=acquisition._acquisition_source(request, inspected, entries),
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
    file: UploadFile = _PACKAGE_UPLOAD,
    allow_untrusted: bool = False,
    approved_permissions: list[str] | None = _APPROVED_PERMISSIONS,
    admin_password: str | None = Form(default=None),
    confirm_dangerous: bool = _CONFIRM_DANGEROUS,
    admin: User = _PLUGIN_ADMIN,
    db: AsyncSession = _PLUGIN_DB,
    operation: Literal["update", "replace"] = "update",
    version_change_confirmed: bool = False,
    expected_installed_version: str | None = Form(default=None, min_length=1, max_length=64),
    expected_digest: str | None = Form(default=None, min_length=64, max_length=64),
) -> dict[str, Any]:
    """Apply uploaded bytes only while the reviewed installed-version snapshot matches."""
    return await _update_plugin_package(
        plugin_id,
        file,
        operation=operation,
        allow_untrusted=allow_untrusted,
        approved_permissions=approved_permissions,
        admin_password=admin_password,
        confirm_dangerous=confirm_dangerous,
        version_change_confirmed=version_change_confirmed,
        expected_installed_version=expected_installed_version
        if isinstance(expected_installed_version, str)
        else None,
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
    version_change_confirmed: bool = False,
    expected_installed_version: str | None = None,
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
            version_change_confirmed=version_change_confirmed,
            expected_installed_version=expected_installed_version,
        ),
        source_metadata=source_metadata,
        admin=admin,
        db=db,
        plugin_id=plugin_id,
        operation=operation,
    )
