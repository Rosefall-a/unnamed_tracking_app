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
import os
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from cryptography.exceptions import InvalidSignature
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.plugin_permissions import (
    PluginPermissionGrant,
)

from .backend_routes import BackendRouteConflictError, validate_host_route_ownership
from .capabilities import (
    PermissionDelta,
    calculate_permission_delta,
    capability_definition,
    package_identity_can_retain_grants,
    permission_key,
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
    DependencyPlan,
    DependencyPlanItem,
    DependencyState,
    plan_dependencies,
)
from .installation_transaction import commit_installation
from .lifecycle_lock import serialized_lifecycle
from .manager_state import manager_state
from .runtime_client import PluginRuntimeClient
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
    """Signature verification and publisher evidence kept separate from consent."""

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
        """Whether this package can retain grants for the same verified publisher."""
        return self.status is PackageTrustStatus.TRUSTED


@dataclass(frozen=True, slots=True)
class InspectedPackage:
    """Verified archive bytes paired with their independently evaluated trust."""

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

    # Consent records distinct administrator decisions rather than service responsibilities.
    # pylint: disable=too-many-instance-attributes

    allow_untrusted: bool = False
    approved_permissions: tuple[str, ...] = ()
    admin_password: str | None = None
    confirm_dangerous: bool = False
    expected_digest: str | None = None
    permissions_reviewed: bool = False
    version_change_confirmed: bool = False
    expected_installed_version: str | None = None


@dataclass(frozen=True, slots=True)
class InstallationPlan:
    """Identity, dependency and grant decisions recomputed before activation."""

    inspected: InspectedPackage
    installation_id: UUID
    dependencies: DependencyPlan
    permissions: PermissionDelta
    installed: dict[str, Any] | None = None
    can_retain_grants: bool = False


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

    def inspect_snapshot(self, package: bytes) -> InspectedPackage:
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
        allow_non_newer: bool = False,
        expected_installed_version: str | None = None,
    ) -> InstallationPlan:
        """Compare only this installation's identity, declarations and grants."""
        manifest = inspected.package.manifest
        installed_plugins = await self.runtime.plugins()
        installed = next(
            (item for item in installed_plugins if item.get("plugin_id") == plugin_id), None
        )
        if installed is None or not installed.get("installation_id"):
            raise InstallationError(409, "Plugin installation identity is missing.")
        if (
            expected_installed_version is not None
            and installed.get("version") != expected_installed_version
        ):
            raise InstallationError(
                409, "The installed plugin changed after review. Review the package again."
            )
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
        if (
            operation == "update"
            and not allow_non_newer
            and parse_semver(manifest.version)
            <= parse_semver(str(installed.get("version", "0.0.0")))
        ):
            raise InstallationError(
                409, "Confirm applying the same version or a downgrade after reviewing the package."
            )
        if operation == "reinstall" and (
            manifest.version != installed.get("version")
            or manifest.integrity.sha256 != installed.get("digest")
        ):
            raise InstallationError(
                409, "Reinstall must use the exact installed release and digest."
            )
        installation_id = UUID(str(installed["installation_id"]))
        can_retain = self._can_retain_grants(inspected, installed, operation)
        delta = await self._permission_delta(
            db,
            plugin_id,
            installation_id,
            installed,
            inspected,
            can_retain=can_retain,
            operation=operation,
        )
        dependencies = plan_dependencies(
            manifest, (item for item in installed_plugins if item.get("plugin_id") != plugin_id)
        )
        return InstallationPlan(
            inspected, installation_id, dependencies, delta, installed, can_retain
        )

    @staticmethod
    def _can_retain_grants(
        inspected: InspectedPackage, installed: dict[str, Any], operation: str
    ) -> bool:
        installed_trust = installed.get("trust")
        installed_trust = installed_trust if isinstance(installed_trust, dict) else {}
        previous_identity = PluginPackageIdentity(
            plugin_id=inspected.package.manifest.plugin_id,
            publisher_key_id=installed_trust.get("publisher_key_id") or installed.get("publisher"),
        )
        candidate_identity = PluginPackageIdentity(
            plugin_id=inspected.package.manifest.plugin_id,
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
                item.get("version") == inspected.package.manifest.version
                and item.get("digest") == inspected.package.manifest.integrity.sha256
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
        return can_retain

    @staticmethod
    async def _permission_delta(
        db: AsyncSession,
        plugin_id: str,
        installation_id: UUID,
        installed: dict[str, Any],
        inspected: InspectedPackage,
        *,
        can_retain: bool,
        operation: str,
    ) -> PermissionDelta:
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
            tuple(permission.capability for permission in inspected.package.manifest.permissions),
            grants if can_retain else (),
        )
        if operation == "rollback":
            delta = delta.model_copy(update={"newly_requested_grants": ()})
        return delta

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
        if consent.permissions_reviewed and not consent.expected_digest:
            raise InstallationError(400, "Permission review requires the reviewed package digest.")
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

    async def _plan_install(self, inspected: InspectedPackage) -> InstallationPlan:
        manifest = inspected.package.manifest
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
        return InstallationPlan(
            inspected,
            uuid4(),
            plan_dependencies(manifest, installed),
            calculate_permission_delta(
                (), tuple(permission.capability for permission in manifest.permissions), ()
            ),
        )

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
        inspected = await asyncio.to_thread(self.inspect_snapshot, package)
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
            plan = await self.plan_update(
                update_plugin_id,
                inspected,
                db,
                operation=operation,
                allow_non_newer=consent.version_change_confirmed,
                expected_installed_version=consent.expected_installed_version,
            )
        else:
            plan = await self._plan_install(inspected)
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
            if not consent.permissions_reviewed and not new_keys.issubset(
                set(consent.approved_permissions)
            ):
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
        return await commit_installation(
            self.runtime,
            plan,
            package,
            consent=consent,
            admin=admin,
            db=db,
            source=source,
            dangerous=dangerous,
            operation=operation,
        )


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
    "permission_key",
]
