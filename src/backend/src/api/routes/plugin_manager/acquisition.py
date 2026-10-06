"""Package acquisition, validation, install preview and installation consent."""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import socket
import tempfile
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import UploadFile as StarletteUploadFile

from src.core.auth import verify_password
from src.database.models.user import User
from src.database.session import get_db
from src.plugin_api.capabilities import capability_children, capability_definition
from src.plugin_api.compatibility import (
    LEGACY_WARNING,
    is_legacy_contract,
    legacy_plugin_allowed,
    manifest_compatibility_checks,
)
from src.plugin_api.contracts import (
    PLUGIN_API_CONTRACT_VERSION,
    CompatibilityStatus,
    evaluate_manifest_compatibility,
    parse_semver,
)
from src.plugin_api.installer import (
    DependencyPlan,
    InspectedPackage,
    InstallationConsent,
    InstallationError,
    PluginInstaller,
    inspect_package,
    plan_dependencies,
)
from src.plugin_api.management_auth import get_plugin_manager_admin
from src.plugin_api.manager_state import manager_state
from src.plugin_api.package_metadata import package_readme
from src.plugin_api.publisher_trust import PublisherTrustError, load_trusted_publishers
from src.plugin_api.runtime_client import PluginRuntimeRequestError, PluginRuntimeUnavailable
from src.plugin_api.updates import (
    PackageFormatError,
    PackageVerificationError,
    PluginPackageVerifier,
)

from . import catalogues, models, runtime, updates

router = APIRouter(prefix="/api/plugins", tags=["plugins"])
logger = logging.getLogger(__name__)


_MAX_PLUGIN_PACKAGE_BYTES = 64 * 1024 * 1024


_REMOTE_FETCH_TIMEOUT = httpx.Timeout(20.0, connect=5.0)


_MAX_REMOTE_REDIRECTS = 3


def _plugin_package_verifier() -> PluginPackageVerifier:
    configured_path = os.getenv("PLUGIN_TRUSTED_PUBLISHER_REGISTRY")
    try:
        publishers = load_trusted_publishers(Path(configured_path) if configured_path else None)
    except PublisherTrustError as exc:
        raise RuntimeError("PLUGIN_TRUSTED_PUBLISHER_REGISTRY is invalid") from exc
    return PluginPackageVerifier(publishers=publishers, require_signature=False)


async def _store_plugin_upload(file: StarletteUploadFile, prefix: str) -> tuple[Path, str, int]:
    filename = file.filename or "plugin-package"
    with tempfile.NamedTemporaryFile(prefix=prefix, suffix=".utp", delete=False) as handle:
        path = Path(handle.name)
        total = 0
        too_large = False
        while chunk := await file.read(1024 * 1024):
            total += len(chunk)
            if total > _MAX_PLUGIN_PACKAGE_BYTES:
                too_large = True
                break
            handle.write(chunk)
    if too_large:
        path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=413,
            detail="Plugin package exceeds the 64 MiB upload limit.",
        )
    return path, filename, total


def _validate_remote_url(raw_url: str) -> str:
    """Allow only public HTTP(S) destinations and standard web ports."""
    try:
        parsed = urlparse(raw_url)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid plugin download URL.") from exc
    if parsed.scheme not in {"http", "https"} or parsed.username or parsed.password:
        raise HTTPException(
            status_code=400,
            detail="Plugin download URLs must use HTTP(S) without embedded credentials.",
        )
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=400, detail="Plugin download URL has no hostname.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise HTTPException(
            status_code=400, detail="Plugin download URL has an invalid port."
        ) from exc
    if port is not None and port not in {80, 443}:
        raise HTTPException(
            status_code=400, detail="Plugin download URLs may only use ports 80 and 443."
        )
    try:
        addresses = {
            ipaddress.ip_address(info[4][0])
            for info in socket.getaddrinfo(
                hostname, port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM
            )
        }
    except OSError as exc:
        raise HTTPException(
            status_code=400, detail="Plugin download hostname could not be resolved."
        ) from exc
    if not addresses or not all(address.is_global for address in addresses):
        raise HTTPException(
            status_code=400,
            detail="Plugin download URL must resolve only to public internet addresses.",
        )
    return parsed.geturl()


async def _download_remote_file(
    raw_url: str, *, json_document: bool = False
) -> tuple[Path, str, int]:
    """Download a bounded public resource without following unvalidated redirects."""
    url = _validate_remote_url(raw_url)
    for _ in range(_MAX_REMOTE_REDIRECTS + 1):
        async with httpx.AsyncClient(
            timeout=_REMOTE_FETCH_TIMEOUT,
            follow_redirects=False,
            headers={"User-Agent": "UnnamedTrackingApp-PluginManager/1"},
        ) as client:
            try:
                async with client.stream("GET", url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise HTTPException(
                                status_code=502,
                                detail="Plugin download redirect has no destination.",
                            )
                        url = _validate_remote_url(urljoin(url, location))
                        continue
                    if response.status_code != 200:
                        raise HTTPException(
                            status_code=502,
                            detail=(f"Plugin download returned HTTP {response.status_code}."),
                        )
                    max_bytes = 1 * 1024 * 1024 if json_document else _MAX_PLUGIN_PACKAGE_BYTES
                    suffix = ".json" if json_document else ".utp"
                    filename = Path(urlparse(url).path).name or f"plugin-download{suffix}"
                    if not json_document and Path(filename).suffix.lower() not in {
                        ".utp",
                        ".zip",
                    }:
                        filename = f"{filename}.utp"
                    with tempfile.NamedTemporaryFile(
                        prefix="plugin-remote-",
                        suffix=suffix,
                        delete=False,
                    ) as handle:
                        path = Path(handle.name)
                        total = 0
                        too_large = False
                        async for chunk in response.aiter_bytes():
                            total += len(chunk)
                            if total > max_bytes:
                                too_large = True
                                break
                            handle.write(chunk)
                    if too_large:
                        path.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail="Remote plugin resource exceeds the allowed size.",
                        )
                    return path, filename, total
            except httpx.HTTPError as exc:
                raise HTTPException(status_code=502, detail="Plugin download failed.") from exc
    raise HTTPException(status_code=502, detail="Plugin download followed too many redirects.")


def _inspect_install_candidate(path: Path) -> InspectedPackage:
    verifier = _plugin_package_verifier()
    try:
        return inspect_package(path, verifier)
    except (PackageFormatError, PackageVerificationError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_package",
                "trust_status": "invalid_package",
                "message": str(exc),
            },
        ) from exc


def _permission_key(name: str, version: int) -> str:
    return f"{name}:v{version}"


def _permission_preview(permission: Any) -> dict[str, Any]:
    definition = capability_definition(permission.capability.name)
    return {
        "key": _permission_key(
            permission.capability.name.value,
            permission.capability.version,
        ),
        "capability": permission.capability.name.value,
        "capability_version": permission.capability.version,
        "rationale": permission.rationale,
        "title": definition.title,
        "category": definition.category,
        "parent": definition.parent.value if definition.parent else None,
        "children": [child.value for child in capability_children(permission.capability.name)],
        "risk": definition.risk.value,
        "highly_privileged": definition.highly_privileged,
    }


def _install_preview(
    inspected: InspectedPackage,
    dependency_plan: DependencyPlan | None = None,
    *,
    source: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = inspected.package.manifest
    trust = inspected.trust
    allow_legacy = legacy_plugin_allowed(
        manifest.plugin_id, manager_state().read()["plugins"].get(manifest.plugin_id)
    )
    compatibility = evaluate_manifest_compatibility(
        manifest,
        os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
        os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
        allow_legacy=allow_legacy,
    )
    checks = manifest_compatibility_checks(
        manifest,
        os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
        os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
        allow_legacy=allow_legacy,
    )
    legacy = allow_legacy and is_legacy_contract(manifest.api_contract_version)
    readme = None
    icon = manifest.icon
    if inspected.package.package_path.exists():
        with zipfile.ZipFile(inspected.package.package_path) as archive:
            import base64

            for name, content_type in (
                ("payload/icon.svg", "image/svg+xml"),
                ("payload/icon.png", "image/png"),
            ):
                if name in archive.namelist() and archive.getinfo(name).file_size <= 256 * 1024:
                    icon = f"data:{content_type};base64," + base64.b64encode(
                        archive.read(name)
                    ).decode("ascii")
                    break
            readme = package_readme(archive)
    dependency_items = (
        [
            {
                "plugin_id": item.plugin_id,
                "version_range": item.version_range,
                "optional": item.optional,
                "state": item.state.value,
                "installed_version": item.installed_version,
                "available_version": item.available_version,
                "source_url": item.source_url,
            }
            for item in dependency_plan.items
        ]
        if dependency_plan is not None
        else [
            {
                "plugin_id": dependency.plugin_id,
                "version_range": dependency.version_range,
                "optional": dependency.optional,
                "state": "unresolved",
                "installed_version": None,
                "available_version": None,
                "source_url": None,
            }
            for dependency in manifest.dependencies
        ]
    )
    return {
        "plugin_id": manifest.plugin_id,
        "name": manifest.name,
        "description": manifest.description,
        "icon": icon,
        "tags": inspected.package.distribution.get("tags", list(manifest.tags)),
        "automatic_update": manifest.automatic_update
        and inspected.package.distribution.get("automatic_update", True),
        "release_notes": inspected.package.distribution.get("release_notes"),
        "readme": readme,
        "version": manifest.version,
        "publisher": trust.publisher_identity,
        "publisher_key_id": trust.publisher_key_id,
        "publisher_channel": trust.publisher_channel,
        "signing_version": inspected.package.signing_version,
        "digest": manifest.integrity.sha256,
        "trust_status": trust.status.value,
        "trust_warning": trust.warning,
        "signature_present": trust.signature_present,
        "signature_verified": trust.signature_verified,
        "installable": trust.installable and compatibility.status == CompatibilityStatus.COMPATIBLE,
        "api_contract_version": manifest.api_contract_version,
        "host_api_contract_version": PLUGIN_API_CONTRACT_VERSION,
        "host_sdk_version": os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
        "host_application_version": os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
        "compatibility_reason": compatibility.reason
        if compatibility.status != CompatibilityStatus.COMPATIBLE
        else "",
        "compatibility_checks": checks,
        "legacy_compatibility": legacy,
        "compatibility_warning": LEGACY_WARNING if legacy else None,
        "sdk_version_range": manifest.sdk_version_range,
        "application_version_range": manifest.application_version_range,
        "dependencies": dependency_items,
        "dependency_ready": dependency_plan.ready
        if dependency_plan is not None
        else not dependency_items,
        "dependency_order": list(dependency_plan.installation_order) if dependency_plan else [],
        "dependency_conflicts": list(dependency_plan.conflicts) if dependency_plan else [],
        "permissions": [_permission_preview(permission) for permission in manifest.permissions],
        "requires_elevated_reauthentication": (
            not trust.is_verified
            and any(
                capability_definition(permission.capability.name).highly_privileged
                for permission in manifest.permissions
            )
        ),
        "source": source or {"type": "upload"},
        "ui": {
            "pages": list(manifest.ui.pages),
            "menus": list(manifest.ui.menus),
            "has_custom_frontend": manifest.frontend is not None,
        },
    }


async def _plan_candidate_dependencies(
    manifest: Any,
    *,
    available: list[dict[str, Any]] | None = None,
) -> DependencyPlan:
    if not manifest.dependencies:
        return plan_dependencies(manifest, ())
    try:
        installed = await runtime._client.plugins()
    except PluginRuntimeRequestError as exc:
        raise runtime._runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    return plan_dependencies(manifest, installed, available or ())


async def _resolve_plugin_upload(request: Request, file: UploadFile | None) -> StarletteUploadFile:
    """Resolve HTTP uploads while remaining compatible with direct route tests."""
    if isinstance(request, StarletteUploadFile):
        return request
    if isinstance(file, StarletteUploadFile):
        return file
    content_type = (request.headers.get("content-type") or "").lower()
    if content_type.startswith("multipart/"):
        form = await request.form()
        for value in form.values():
            if isinstance(value, StarletteUploadFile):
                return value
    raise HTTPException(
        status_code=400,
        detail={
            "code": "plugin_file_missing",
            "message": "Upload a .utp package as a multipart file.",
        },
    )


async def _validate_catalogue_candidate(
    path: Path, inspected: InspectedPackage, request: models.PluginInstallUrl, admin: User
) -> list[models.PluginCatalogEntry]:
    """Bind every catalogue acquisition to its advertised identity and hashes."""
    if request.source_type != "catalogue":
        return []
    if not request.catalogue_url:
        raise HTTPException(422, "Catalogue URL is required for a catalogue package.")
    entries = await catalogues.plugin_catalog(source=request.catalogue_url, user=admin)
    manifest = inspected.package.manifest
    entry = next((item for item in entries if item.plugin_id == manifest.plugin_id), None)
    release = (
        entry
        if entry and entry.version == manifest.version
        else next((item for item in entry.releases if item.version == manifest.version), None)
        if entry
        else None
    )
    if (
        release is None
        or release.url != request.url
        or release.digest
        and release.digest.lower() != manifest.integrity.sha256.lower()
        or release.package_sha256
        and release.package_sha256.lower() != hashlib.sha256(path.read_bytes()).hexdigest()
    ):
        raise HTTPException(409, "Catalogue release and package identity or hashes differ.")
    return entries


def _acquisition_source(
    request: models.PluginInstallUrl,
    inspected: InspectedPackage,
    entries: list[models.PluginCatalogEntry],
) -> dict[str, Any]:
    """Historical selection is derived from checked catalogue data, never a client flag."""
    source: dict[str, Any] = {
        "type": request.source_type,
        "url": request.url,
        "catalogue_url": request.catalogue_url,
        "release_notes": request.release_notes,
        "changelog_url": request.changelog_url,
    }
    manifest = inspected.package.manifest
    entry = next((item for item in entries if item.plugin_id == manifest.plugin_id), None)
    if entry is not None:
        source["latest_version"] = entry.version
        source["version_pin"] = (
            manifest.version
            if parse_semver(manifest.version) < parse_semver(entry.version)
            else None
        )
    return source


@router.post("/install/preview-url")
async def preview_plugin_install_url(
    request: models.PluginInstallUrl, admin: User = Depends(get_plugin_manager_admin)
) -> dict[str, Any]:
    """Download and statically inspect a remote .utp/.zip package."""
    path: Path | None = None
    try:
        path, filename, total = await _download_remote_file(request.url)
        inspected = _inspect_install_candidate(path)
        entries = await _validate_catalogue_candidate(path, inspected, request, admin)
        available = [entry.model_dump() for entry in entries]
        dependencies = await _plan_candidate_dependencies(
            inspected.package.manifest,
            available=available,
        )
        source = _acquisition_source(request, inspected, entries)
        return {
            **_install_preview(inspected, dependencies, source=source),
            "source_url": request.url,
            "download_filename": filename,
            "download_bytes": total,
        }
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


@router.post("/install/url", status_code=201)
async def install_plugin_url(
    request: models.PluginInstallUrl,
    allow_untrusted: bool = False,
    approved_permissions: list[str] | None = Query(default=None),
    admin: User = Depends(get_plugin_manager_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Download a remote package and send it through the same install/consent path."""
    path: Path | None = None
    upload: UploadFile | None = None
    try:
        path, filename, _ = await _download_remote_file(request.url)
        inspected = _inspect_install_candidate(path)
        entries = await _validate_catalogue_candidate(path, inspected, request, admin)
        upload = UploadFile(path.open("rb"), filename=filename)
        return await _install_plugin_package(
            upload,
            allow_untrusted=allow_untrusted,
            approved_permissions=approved_permissions,
            admin_password=request.admin_password,
            confirm_dangerous=request.confirm_dangerous,
            expected_digest=request.expected_digest,
            source_metadata=_acquisition_source(request, inspected, entries),
            admin=admin,
            db=db,
        )
    finally:
        if upload is not None:
            await upload.close()
        if path is not None:
            path.unlink(missing_ok=True)


@router.post("/install/preview")
async def preview_plugin_install(
    request: Request,
    file: UploadFile | None = File(default=None),
    admin: User = Depends(get_plugin_manager_admin),
) -> dict[str, Any]:
    """Statically inspect an upload for consent without installing or executing it."""
    del admin
    path: Path | None = None
    resolved_file: StarletteUploadFile | None = None
    try:
        resolved_file = await _resolve_plugin_upload(request, file)
        path, filename, total = await _store_plugin_upload(resolved_file, "plugin-preview-")
        inspected = _inspect_install_candidate(path)
        dependencies = await _plan_candidate_dependencies(inspected.package.manifest)
        logger.info(
            "Plugin install preview validated: plugin_id=%s version=%s "
            "filename=%r bytes=%d trust=%s",
            inspected.package.manifest.plugin_id,
            inspected.package.manifest.version,
            filename,
            total,
            inspected.trust.status.value,
        )
        return _install_preview(inspected, dependencies)
    finally:
        if path is not None:
            path.unlink(missing_ok=True)
        if resolved_file is not None:
            await resolved_file.close()


@router.post("/install", status_code=201)
async def install_plugin(
    file: UploadFile = File(...),
    allow_untrusted: bool = False,
    approved_permissions: list[str] | None = Query(default=None),
    admin_password: str | None = Form(default=None),
    confirm_dangerous: bool = Query(default=False),
    admin: User = Depends(get_plugin_manager_admin),
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    return await _install_plugin_package(
        file,
        allow_untrusted=allow_untrusted,
        approved_permissions=approved_permissions,
        admin_password=admin_password,
        confirm_dangerous=confirm_dangerous,
        source_metadata={"type": "upload"},
        admin=admin,
        db=db,
    )


def _plugin_installer() -> PluginInstaller:
    return PluginInstaller(runtime._client, _plugin_package_verifier(), verify_password)


async def _commit_plugin_upload(
    file: UploadFile,
    *,
    consent: InstallationConsent,
    source_metadata: dict[str, Any] | None,
    admin: User,
    db: AsyncSession,
    plugin_id: str | None = None,
    operation: str = "update",
) -> dict[str, Any]:
    """HTTP acquisition adapter; all policy and lifecycle decisions belong to the installer."""
    temporary_path: Path | None = None
    try:
        temporary_path, _, _ = await _store_plugin_upload(file, "plugin-candidate-")
        return await _plugin_installer().install(
            temporary_path.read_bytes(),
            consent=consent,
            admin=admin,
            db=db,
            source=source_metadata,
            update_plugin_id=plugin_id,
            operation=operation,
        )
    except InstallationError as exc:
        detail = exc.detail
        if isinstance(detail, dict):
            if exc.plan is not None:
                plan = exc.plan
                preview = (
                    updates._update_preview(
                        plan.inspected,
                        plan.installed,
                        plan.permissions,
                        plan.dependencies,
                        can_retain_grants=plan.can_retain_grants,
                        source=source_metadata,
                    )
                    if plan.installed is not None
                    else _install_preview(plan.inspected, plan.dependencies, source=source_metadata)
                )
                detail = {**preview, **detail}
            elif exc.inspected is not None:
                detail = {**_install_preview(exc.inspected), **detail}
        raise HTTPException(status_code=exc.status_code, detail=detail) from exc
    except (PackageFormatError, PackageVerificationError) as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_package",
                "trust_status": "invalid_package",
                "message": str(exc),
            },
        ) from exc
    except PluginRuntimeRequestError as exc:
        raise runtime._runtime_request_error(exc) from exc
    except PluginRuntimeUnavailable as exc:
        raise runtime._runtime_error(exc) from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        await file.close()


async def _install_plugin_package(
    file: UploadFile,
    *,
    allow_untrusted: bool,
    approved_permissions: list[str] | None,
    admin_password: str | None,
    confirm_dangerous: bool,
    source_metadata: dict[str, Any],
    admin: User,
    db: AsyncSession,
    expected_digest: str | None = None,
) -> dict[str, Any]:
    return await _commit_plugin_upload(
        file,
        consent=InstallationConsent(
            allow_untrusted=allow_untrusted,
            approved_permissions=tuple(approved_permissions)
            if isinstance(approved_permissions, list)
            else (),
            admin_password=admin_password,
            confirm_dangerous=confirm_dangerous,
            expected_digest=expected_digest,
        ),
        source_metadata=source_metadata,
        admin=admin,
        db=db,
    )
