"""Canonical security policy and lifecycle for plugin installs and updates.

Acquisition is deliberately outside this module. Uploaded files, remote URLs,
and catalogue entries all become a local package path and then pass through the
same inspection, trust, dependency, permission consent, commit and activation
code here. Runtime execution stays behind the isolated runtime boundary.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import os
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import quote
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from sqlalchemy import select, update
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.plugin_permission_audit import PluginPermissionAudit
from src.database.models.plugin_permissions import (
    PluginLifecycleTransaction,
    PluginPermissionGrant,
    PluginPermissionRequest,
)

from .backend_routes import BackendRouteConflictError, validate_host_route_ownership
from .capabilities import (
    PermissionDelta,
    calculate_permission_delta,
    capability_definition,
    package_identity_can_retain_grants,
)
from .compatibility import legacy_plugin_allowed
from .contracts import (
    PLUGIN_API_CONTRACT_VERSION,
    BackendRouteScope,
    CapabilityRef,
    CompatibilityStatus,
    PluginPackageIdentity,
    evaluate_manifest_compatibility,
    parse_semver,
)
from .dependency_plan import (
    DependencyPlan as DependencyPlan,
)
from .dependency_plan import (
    DependencyPlanItem as DependencyPlanItem,
)
from .dependency_plan import (
    DependencyState as DependencyState,
)
from .dependency_plan import (
    plan_dependencies as plan_dependencies,
)
from .lifecycle_lock import serialized_lifecycle
from .manager_state import manager_state
from .runtime_client import PluginRuntimeClient, PluginRuntimeRequestError, PluginRuntimeUnavailable
from .updates import (
    PackageVerificationError,
    PluginPackageVerifier,
    TrustedPublisher,
    VerifiedPackage,
)


class PackageTrustStatus(StrEnum):
    """Package-signature state, intentionally separate from source provenance."""

    TRUSTED = "trusted"
    UNKNOWN_PUBLISHER = "unknown_publisher"
    INVALID_SIGNATURE = "invalid_signature"
    UNSIGNED = "unsigned"


@dataclass(frozen=True, slots=True)
class PackageTrust:
    status: PackageTrustStatus
    signature_present: bool
    signature_verified: bool
    publisher_key_id: str | None
    publisher_identity: str | None
    warning: str | None
    publisher_channel: str = "unverified"

    @property
    def installable(self) -> bool:
        """Invalid signatures are never an administrator-overridable warning."""
        return self.status is not PackageTrustStatus.INVALID_SIGNATURE

    @property
    def is_verified(self) -> bool:
        return self.status is PackageTrustStatus.TRUSTED


@dataclass(frozen=True, slots=True)
class InspectedPackage:
    package: VerifiedPackage
    trust: PackageTrust


def inspect_package(
    package_path: Path,
    verifier: PluginPackageVerifier,
) -> InspectedPackage:
    """Validate package bytes first, then classify signature trust precisely."""
    candidate = verifier.inspect(package_path, verify_signature=False)
    integrity = candidate.manifest.integrity
    signature_present = integrity.signature is not None
    key_id = integrity.key_id

    if not signature_present:
        return InspectedPackage(
            candidate,
            PackageTrust(
                status=PackageTrustStatus.UNSIGNED,
                signature_present=False,
                signature_verified=False,
                publisher_key_id=key_id,
                publisher_identity=None,
                warning="The package is unsigned. Its publisher identity cannot be verified.",
            ),
        )

    if not key_id:
        return InspectedPackage(
            candidate,
            PackageTrust(
                status=PackageTrustStatus.INVALID_SIGNATURE,
                signature_present=True,
                signature_verified=False,
                publisher_key_id=None,
                publisher_identity=None,
                warning="The signed package does not identify a publisher key.",
            ),
        )

    # A signature's encoding/length is verifiable even without a publisher key.
    try:
        assert integrity.signature is not None
        signature_bytes = base64.b64decode(integrity.signature.removeprefix("v2:"), validate=True)
        if len(signature_bytes) != 64:
            raise ValueError("invalid Ed25519 signature length")
        publisher: TrustedPublisher | None = verifier.publishers.get(key_id)
        if publisher is not None:
            publisher.verifier().verify(
                signature_bytes,
                f"plugin-package-v{candidate.signing_version}:{candidate.payload_digest}".encode(
                    "ascii"
                ),
            )
    except (ValueError, binascii.Error, InvalidSignature, PackageVerificationError):
        return InspectedPackage(
            candidate,
            PackageTrust(
                status=PackageTrustStatus.INVALID_SIGNATURE,
                signature_present=True,
                signature_verified=False,
                publisher_key_id=key_id,
                publisher_identity=None,
                warning="The package signature is invalid and installation is blocked.",
            ),
        )

    if publisher is None or not publisher.allows_plugin(candidate.manifest.plugin_id):
        return InspectedPackage(
            candidate,
            PackageTrust(
                status=PackageTrustStatus.UNKNOWN_PUBLISHER,
                signature_present=True,
                signature_verified=False,
                publisher_key_id=key_id,
                publisher_identity=publisher.publisher if publisher else None,
                warning=(
                    "The package is signed, but the publisher key is not trusted for this plugin."
                ),
            ),
        )

    return InspectedPackage(
        candidate,
        PackageTrust(
            status=PackageTrustStatus.TRUSTED,
            signature_present=True,
            signature_verified=True,
            publisher_key_id=key_id,
            publisher_identity=publisher.publisher or None,
            warning=None,
            publisher_channel=publisher.channel
            if candidate.signing_version == 2 or publisher.channel != "official"
            else "community",
        ),
    )


class InstallationError(ValueError):
    """An installation policy rejection, translated to HTTP only by the routes."""

    def __init__(self, status_code: int, detail: str | dict[str, Any]) -> None:
        super().__init__(str(detail))
        self.status_code = status_code
        self.detail = detail
        self.plan: InstallationPlan | None = None
        self.inspected: InspectedPackage | None = None


@dataclass(frozen=True, slots=True)
class InstallationConsent:
    """Explicit administrator decisions; source provenance never grants trust."""

    allow_untrusted: bool = False
    approved_permissions: tuple[str, ...] = ()
    admin_password: str | None = None
    confirm_dangerous: bool = False
    expected_digest: str | None = None


@dataclass(frozen=True, slots=True)
class InstallationPlan:
    inspected: InspectedPackage
    installation_id: UUID
    dependencies: DependencyPlan
    permissions: PermissionDelta
    installed: dict[str, Any] | None = None
    can_retain_grants: bool = False


def permission_key(capability: CapabilityRef) -> str:
    """Stable consent key shared by installs and updates."""
    return f"{capability.name.value}:v{capability.version}"


class PluginInstaller:
    """Own the security-sensitive lifecycle for every acquisition source.

    Acquisition supplies bounded bytes. Inspection uses a private snapshot and
    the exact same bytes are sent to the runtime after consent. The runtime owns
    safe extraction and atomic package replacement; this service owns trust and
    grants and commits them before activation. Dependencies never supply grants.
    """

    def __init__(
        self,
        runtime: PluginRuntimeClient,
        verifier: PluginPackageVerifier,
        password_verifier: Callable[[str, str], bool],
    ) -> None:
        self.runtime = runtime
        self.verifier = verifier
        self.password_verifier = password_verifier

    def _inspect_snapshot(self, package: bytes) -> InspectedPackage:
        with tempfile.TemporaryDirectory(prefix="plugin-candidate-") as directory:
            snapshot = Path(directory) / "package.utp"
            snapshot.write_bytes(package)
            return inspect_package(snapshot, self.verifier)

    async def plan_update(
        self,
        plugin_id: str,
        inspected: InspectedPackage,
        db: AsyncSession,
        *,
        operation: str = "update",
    ) -> InstallationPlan:
        """Compare only this installation's identity, declarations and grants."""
        manifest = inspected.package.manifest
        installed_plugins = await self.runtime.plugins()
        installed = next(
            (item for item in installed_plugins if item.get("plugin_id") == plugin_id), None
        )
        if installed is None or not installed.get("installation_id"):
            raise InstallationError(409, "Plugin installation identity is missing.")
        compatibility = evaluate_manifest_compatibility(
            manifest,
            os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
            os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
            allow_legacy=legacy_plugin_allowed(manifest.plugin_id, installed),
        )
        if compatibility.status != CompatibilityStatus.COMPATIBLE:
            raise InstallationError(409, f"Package is not installable: {compatibility.reason}")
        if manifest.plugin_id != plugin_id:
            raise InstallationError(
                400, "Updated package plugin ID does not match the installed plugin."
            )
        if operation == "update" and parse_semver(manifest.version) <= parse_semver(
            str(installed.get("version", "0.0.0"))
        ):
            raise InstallationError(409, "Plugin update version must be newer.")
        if operation == "reinstall" and (
            manifest.version != installed.get("version")
            or manifest.integrity.sha256 != installed.get("digest")
        ):
            raise InstallationError(
                409, "Reinstall must use the exact installed release and digest."
            )
        installation_id = UUID(str(installed["installation_id"]))
        installed_trust = installed.get("trust")
        installed_trust = installed_trust if isinstance(installed_trust, dict) else {}
        previous_identity = PluginPackageIdentity(
            plugin_id=plugin_id,
            publisher_key_id=installed_trust.get("publisher_key_id") or installed.get("publisher"),
        )
        candidate_identity = PluginPackageIdentity(
            plugin_id=manifest.plugin_id,
            publisher_key_id=inspected.trust.publisher_key_id,
        )
        can_retain = (
            installed_trust.get("status") == PackageTrustStatus.TRUSTED.value
            and inspected.trust.is_verified
            and package_identity_can_retain_grants(previous_identity, candidate_identity)
        )
        if operation == "reinstall":
            can_retain = True
        if operation == "rollback":
            if not any(
                item.get("version") == manifest.version
                and item.get("digest") == manifest.integrity.sha256
                for item in installed.get("history", [])
            ):
                raise InstallationError(409, "Rollback must use a retained package.")
            can_retain = True
        if operation == "replace":
            can_retain = False
        if (
            installed_trust.get("status") == PackageTrustStatus.TRUSTED.value
            and not can_retain
            and operation != "replace"
        ):
            raise InstallationError(
                409,
                "The verified update publisher does not match the installed package. "
                "Install it as a new lifecycle instance and review permissions again.",
            )
        grant_rows = (
            await db.execute(
                select(
                    PluginPermissionGrant.capability, PluginPermissionGrant.capability_version
                ).where(
                    PluginPermissionGrant.plugin_id == plugin_id,
                    PluginPermissionGrant.installation_id == installation_id,
                    PluginPermissionGrant.revoked_at.is_(None),
                )
            )
        ).all()
        grants = tuple(CapabilityRef(name=name, version=version) for name, version in grant_rows)
        previous = (
            tuple(CapabilityRef.model_validate(ref) for ref in installed.get("permission_refs", []))
            if can_retain
            else ()
        )
        delta = calculate_permission_delta(
            previous,
            tuple(permission.capability for permission in manifest.permissions),
            grants if can_retain else (),
        )
        if operation == "rollback":
            delta = delta.model_copy(update={"newly_requested_grants": ()})
        dependencies = plan_dependencies(
            manifest, (item for item in installed_plugins if item.get("plugin_id") != plugin_id)
        )
        return InstallationPlan(
            inspected, installation_id, dependencies, delta, installed, can_retain
        )

    def confirm(
        self, plan: InstallationPlan, consent: InstallationConsent, admin: Any
    ) -> list[str]:
        """One consent and reauthentication rule for installs and permission increases."""
        trust = plan.inspected.trust
        if not trust.installable:
            raise InstallationError(400, {"code": "invalid_signature", "message": trust.warning})
        if not trust.is_verified and not consent.allow_untrusted:
            raise InstallationError(
                409,
                {"code": "untrusted_plugin", "message": "Explicit unverified consent is required."},
            )
        if not plan.dependencies.ready:
            raise InstallationError(
                409,
                {
                    "code": "dependency_resolution_failed",
                    "message": "Required plugin dependencies must be installed compatibly first.",
                },
            )
        new_keys = {permission_key(ref) for ref in plan.permissions.newly_requested_grants}
        approved = set(consent.approved_permissions)
        if not approved.issubset(new_keys):
            raise InstallationError(400, "Consent contains an undeclared or unchanged permission.")
        dangerous = [
            permission_key(ref)
            for ref in plan.permissions.newly_requested_grants
            if permission_key(ref) in approved
            and capability_definition(ref.name).highly_privileged
            and not trust.is_verified
        ]
        if dangerous:
            if not consent.confirm_dangerous:
                raise InstallationError(
                    409,
                    {
                        "code": "dangerous_permissions_confirmation_required",
                        "message": "Explicit confirmation is required for dangerous unverified permissions.",
                        "permissions": dangerous,
                    },
                )
            if not consent.admin_password or not self.password_verifier(
                consent.admin_password, getattr(admin, "password_hash", "")
            ):
                raise InstallationError(
                    401,
                    {
                        "code": "administrator_reauthentication_failed",
                        "message": "Administrator password re-entry is required for these permissions.",
                        "permissions": dangerous,
                    },
                )
        return dangerous

    @serialized_lifecycle
    async def install(
        self,
        package: bytes,
        *,
        consent: InstallationConsent,
        admin: Any,
        db: AsyncSession,
        source: dict[str, Any] | None = None,
        update_plugin_id: str | None = None,
        operation: str = "update",
    ) -> dict[str, Any]:
        """Validate, resolve, authorize, atomically install, then activate and check health."""
        if len(package) > self.verifier.max_package_bytes:
            raise InstallationError(413, "Plugin package exceeds the 64 MiB upload limit.")
        inspected = await asyncio.to_thread(self._inspect_snapshot, package)
        manifest = inspected.package.manifest
        if not inspected.trust.installable:
            error = InstallationError(
                400, {"code": "invalid_signature", "message": inspected.trust.warning}
            )
            error.inspected = inspected
            raise error
        if (
            consent.expected_digest
            and inspected.package.payload_digest.lower() != consent.expected_digest.lower()
        ):
            raise InstallationError(
                409, "The remote plugin changed after preview; review it again before installing."
            )
        if update_plugin_id is not None:
            plan = await self.plan_update(update_plugin_id, inspected, db, operation=operation)
        else:
            compatibility = evaluate_manifest_compatibility(
                manifest,
                os.getenv("PLUGIN_SDK_VERSION", PLUGIN_API_CONTRACT_VERSION),
                os.getenv("PLUGIN_APPLICATION_VERSION", "1.0.0"),
            )
            if compatibility.status != CompatibilityStatus.COMPATIBLE:
                raise InstallationError(409, f"Package is not installable: {compatibility.reason}")
            installed = await self.runtime.plugins()
            duplicate = next(
                (item for item in installed if item.get("plugin_id") == manifest.plugin_id), None
            )
            duplicate = duplicate or manager_state().read()["plugins"].get(manifest.plugin_id)
            if duplicate is not None:
                raise InstallationError(
                    409,
                    {
                        "code": "already_installed",
                        "plugin_id": manifest.plugin_id,
                        "installed_version": duplicate.get("version"),
                        "message": "Plugin is already installed. Choose update, reinstall, replace, or cancel.",
                        "choices": ["update", "reinstall", "replace", "cancel"],
                    },
                )
            plan = InstallationPlan(
                inspected,
                uuid4(),
                plan_dependencies(manifest, installed),
                calculate_permission_delta(
                    (), tuple(permission.capability for permission in manifest.permissions), ()
                ),
            )
        if any(route.scope is BackendRouteScope.HOST for route in manifest.backend_routes):
            try:
                validate_host_route_ownership(
                    await self.runtime.plugins(),
                    candidate_plugin_id=manifest.plugin_id,
                    candidate_routes=manifest.backend_routes,
                )
            except BackendRouteConflictError as exc:
                raise InstallationError(
                    409, {"code": "plugin_route_conflict", "message": str(exc)}
                ) from exc
        try:
            dangerous = self.confirm(plan, consent, admin)
        except InstallationError as exc:
            exc.plan = plan
            raise
        if plan.installed is not None:
            new_keys = {permission_key(ref) for ref in plan.permissions.newly_requested_grants}
            if not new_keys.issubset(set(consent.approved_permissions)):
                manager_state().stage(
                    manifest.plugin_id,
                    package,
                    {
                        "version": manifest.version,
                        "available_version": manifest.version,
                        "digest": manifest.integrity.sha256,
                        "status": "awaiting_permissions",
                        "source": source,
                        "new_permission_keys": sorted(new_keys),
                    },
                )
                return {
                    "plugin_id": manifest.plugin_id,
                    "version": plan.installed["version"],
                    "available_version": manifest.version,
                    "status": "awaiting_permissions",
                    "healthy": plan.installed.get("health") == "healthy",
                }
        return await self._commit(plan, package, consent, admin, db, source, dangerous, operation)

    async def _commit(
        self,
        plan: InstallationPlan,
        package: bytes,
        consent: InstallationConsent,
        admin: Any,
        db: AsyncSession,
        source: dict[str, Any] | None,
        dangerous: list[str],
        operation: str,
    ) -> dict[str, Any]:
        manifest = plan.inspected.package.manifest
        trust = plan.inspected.trust
        plugin_id = manifest.plugin_id
        now = int(time.time())
        approved = set(consent.approved_permissions)
        replacing = plan.installed is not None
        previous = {
            **manager_state().read()["plugins"].get(plugin_id, {}),
            **(plan.installed or {}),
        }
        selected_source = source or previous.get("source", {"type": "upload"})
        latest = selected_source.get("latest_version")
        older = bool(latest and parse_semver(manifest.version) < parse_semver(latest))
        if previous.get("version"):
            older = older or parse_semver(manifest.version) < parse_semver(previous["version"])
        pin = manifest.version if older or operation == "rollback" else None
        if operation == "reinstall" and previous.get("version_pin") == manifest.version:
            pin = manifest.version
        update_policy = {
            "version_pin": pin,
            "automatic_updates": "disabled" if pin else previous.get("automatic_updates", "follow"),
        }
        operation_id = str(uuid4())
        prepared = False
        commit_attempted = False
        removed_grants: list[UUID] = []
        added_grants: list[PluginPermissionGrant] = []
        try:
            if replacing and not plan.can_retain_grants:
                previous_grants = await db.scalars(
                    select(PluginPermissionGrant).where(
                        PluginPermissionGrant.plugin_id == plugin_id,
                        PluginPermissionGrant.installation_id == plan.installation_id,
                        PluginPermissionGrant.revoked_at.is_(None),
                    )
                )
                removed_grants.extend(grant.id for grant in previous_grants)
                await db.execute(
                    update(PluginPermissionGrant)
                    .where(
                        PluginPermissionGrant.plugin_id == plugin_id,
                        PluginPermissionGrant.installation_id == plan.installation_id,
                        PluginPermissionGrant.revoked_at.is_(None),
                    )
                    .values(revoked_at=now, revoked_by_operation=UUID(operation_id))
                )
            rows: list[Any] = []
            for ref in plan.permissions.newly_requested_grants:
                allowed = permission_key(ref) in approved
                rationale = next(p.rationale for p in manifest.permissions if p.capability == ref)
                identity = {
                    "plugin_id": plugin_id,
                    "installation_id": plan.installation_id,
                    "capability": ref.name.value,
                    "capability_version": ref.version,
                }
                rows.append(
                    PluginPermissionRequest(
                        **identity,
                        rationale=rationale,
                        status="approved" if allowed else "denied",
                        resolved_at=now,
                        resolved_by=getattr(admin, "id", None),
                    )
                )
                if allowed:
                    grant = PluginPermissionGrant(id=uuid4(), **identity)
                    rows.append(grant)
                    added_grants.append(grant)
                rows.append(
                    PluginPermissionAudit(
                        **identity,
                        user_id=getattr(admin, "id", None),
                        decision="allowed" if allowed else "denied",
                        reason="administrator update consent"
                        if replacing
                        else "administrator install consent",
                    )
                )
            db.add_all(rows)
            options: dict[str, Any] = {
                "installation_id": str(plan.installation_id),
                "operation_id": operation_id,
                "source_metadata": source,
                "trust_metadata": {
                    "status": trust.status.value,
                    "signature_present": trust.signature_present,
                    "signature_verified": trust.signature_verified,
                    "publisher_key_id": trust.publisher_key_id,
                    "publisher_identity": trust.publisher_identity,
                    "publisher_channel": trust.publisher_channel,
                    "signing_version": plan.inspected.package.signing_version,
                },
            }
            if replacing:
                options["replace"] = True
                assert plan.installed is not None
                options["expected_version"] = str(plan.installed["version"])
            result = await self.runtime.install_package(
                package, f"{plugin_id}-{manifest.version}.utp", **options
            )
            if result.get("operation_id") != operation_id:
                raise PluginRuntimeRequestError(
                    "runtime did not prepare the installation transaction"
                )
            prepared = True
            manager_state().patch(
                plugin_id,
                **{
                    **(plan.installed or {}),
                    **update_policy,
                    "plugin_id": plugin_id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "api_contract_version": manifest.api_contract_version,
                    "sdk_version_range": manifest.sdk_version_range,
                    "application_version_range": manifest.application_version_range,
                    "description": manifest.description,
                    "installation_id": str(plan.installation_id),
                    "digest": manifest.integrity.sha256,
                    "permissions": [p.capability.name.value for p in manifest.permissions],
                    "permission_refs": [
                        p.capability.model_dump(mode="json") for p in manifest.permissions
                    ],
                    "source": selected_source,
                    "trust": options["trust_metadata"],
                    "status": "stopped",
                    "enabled": False,
                    "compatible": True,
                    "health": "unknown",
                },
            )
            if plan.can_retain_grants:
                removed = {(ref.name.value, ref.version) for ref in plan.permissions.removed}
                for grant in await db.scalars(
                    select(PluginPermissionGrant).where(
                        PluginPermissionGrant.plugin_id == plugin_id,
                        PluginPermissionGrant.installation_id == plan.installation_id,
                        PluginPermissionGrant.revoked_at.is_(None),
                    )
                ):
                    if (grant.capability, grant.capability_version) in removed:
                        removed_grants.append(grant.id)
                        grant.revoked_at = now
                        grant.revoked_by_operation = UUID(operation_id)
            receipt = PluginLifecycleTransaction(
                id=UUID(operation_id),
                plugin_id=plugin_id,
                user_id=getattr(admin, "id", None),
                added_grants=[str(grant.id) for grant in added_grants],
                removed_grants=[str(grant_id) for grant_id in removed_grants],
                grant_timestamp=now,
                completed=False,
            )
            db.add_all([receipt])
            commit_attempted = True
            await db.commit()
        except Exception as exc:
            await db.rollback()
            # A lost COMMIT acknowledgement is not proof of rollback. Restoring
            # old unverified code could expose it to a newly committed grant.
            # Only abort on a definite rejection or an error before COMMIT.
            definite_rejection = not commit_attempted or isinstance(
                exc, (DataError, IntegrityError)
            )
            if prepared and definite_rejection:
                try:
                    await self.runtime.finish_installation(plugin_id, operation_id, commit=False)
                    if plan.installed:
                        manager_state().patch(
                            plugin_id,
                            **{"version_pin": None, "automatic_updates": "follow", **previous},
                        )
                    else:
                        manager_state().remove(plugin_id)
                except (PluginRuntimeRequestError, PluginRuntimeUnavailable):
                    logging.getLogger(__name__).exception(
                        "Plugin installation remains pending and cannot activate: plugin_id=%s",
                        plugin_id,
                    )
            raise

        # A failed finalization leaves the package durably disabled and pending.
        # Never fall back to start or claim activation on an ambiguous commit.
        await self.runtime.finish_installation(plugin_id, operation_id, commit=True)

        status = result.get("status", "updated" if replacing else "installed")
        healthy = False
        if plan.installed is None or plan.installed.get(
            "activation_requested", plan.installed.get("enabled")
        ):
            try:
                encoded = quote(plugin_id, safe="")
                if manifest.dependencies:
                    dependencies = plan_dependencies(manifest, await self.runtime.plugins())
                    if not dependencies.ready:
                        raise PluginRuntimeRequestError(
                            "plugin dependencies changed before activation"
                        )
                await self.runtime.start(encoded, user_id=str(getattr(admin, "id", "")) or None)
                healthy = await self.runtime.plugin_health(encoded)
                status = "running" if healthy else "unhealthy"
            except (PluginRuntimeRequestError, PluginRuntimeUnavailable) as exc:
                logging.getLogger(__name__).warning(
                    "Plugin activation failed: plugin_id=%s error=%s", plugin_id, exc
                )
                status = "failed_activation"
        failed = status in {"unhealthy", "failed_activation"}
        if replacing and failed:
            # Candidate code is stopped before its grants are withdrawn. Restore
            # only grants this transaction removed; never revive unrelated revocations.
            await self.runtime.stop(quote(plugin_id, safe=""))
            for grant in added_grants:
                await db.execute(
                    update(PluginPermissionGrant)
                    .where(PluginPermissionGrant.id == grant.id)
                    .values(revoked_at=int(time.time()))
                )
            if removed_grants:
                await db.execute(
                    update(PluginPermissionGrant)
                    .where(
                        PluginPermissionGrant.id.in_(removed_grants),
                        PluginPermissionGrant.revoked_by_operation == UUID(operation_id),
                    )
                    .values(revoked_at=None, revoked_by_operation=None)
                )
            await db.commit()
            await self.runtime.finish_activation(plugin_id, operation_id, commit=False)
            manager_state().patch(
                plugin_id,
                version_pin=previous.get("version_pin"),
                automatic_updates=previous.get("automatic_updates", "follow"),
                last_update_error="Candidate failed startup/health; previous release restored.",
            )
            status = "rolled_back"
            healthy = await self.runtime.plugin_health(quote(plugin_id, safe=""))
        else:
            if (
                plan.installed
                and plan.installed.get("enabled")
                and plan.installed.get("status") == "stopped"
            ):
                await self.runtime.stop_runtime(plugin_id)
                status = "stopped"
            await self.runtime.finish_activation(plugin_id, operation_id, commit=True)
            await self.runtime.prune_history(
                plugin_id, int(manager_state().settings()["retained_versions"])
            )
        manager_state().reconcile(await self.runtime.plugins())
        receipt.completed = True
        await db.commit()
        if not failed:
            manager_state().patch(plugin_id, staged_update=None, available_update=None)
            manager_state().stage_path(plugin_id).unlink(missing_ok=True)
        response = {
            "plugin_id": plugin_id,
            "version": plan.installed["version"]
            if status == "rolled_back" and plan.installed
            else manifest.version,
            "permissions_requested": len(plan.permissions.newly_requested_grants),
            "permissions_granted": len(approved),
            "dangerous_permissions_reauthenticated": dangerous,
            "trust_status": trust.status.value,
            "install_status": result.get("status", "updated" if replacing else "installed"),
            "status": status,
            "healthy": healthy,
        }
        if replacing:
            response["permission_delta"] = plan.permissions.model_dump(mode="json")
        else:
            response.update(
                {
                    "name": manifest.name,
                    "publisher": trust.publisher_identity,
                    "publisher_key_id": trust.publisher_key_id,
                    "installation_id": str(plan.installation_id),
                    "permissions_denied": len(plan.permissions.newly_requested_grants)
                    - len(approved),
                    "trust_warning": trust.warning,
                }
            )
        return response


__all__ = [
    "DependencyPlan",
    "DependencyPlanItem",
    "DependencyState",
    "InspectedPackage",
    "InstallationConsent",
    "InstallationError",
    "InstallationPlan",
    "PluginInstaller",
    "PackageTrust",
    "PackageTrustStatus",
    "inspect_package",
    "plan_dependencies",
]
