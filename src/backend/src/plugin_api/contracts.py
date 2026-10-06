"""Stable public Plugin API v1 exports and compatibility decisions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base_contracts import (
    API_VERSION as API_VERSION,
)
from .base_contracts import (
    SEMVER_RE as SEMVER_RE,
)
from .base_contracts import (
    ApiVersion as ApiVersion,
)
from .base_contracts import (
    BackendRouteAuthorization as BackendRouteAuthorization,
)
from .base_contracts import (
    BackendRouteMethod as BackendRouteMethod,
)
from .base_contracts import (
    BackendRouteScope as BackendRouteScope,
)
from .base_contracts import (
    Capability as Capability,
)
from .base_contracts import (
    CapabilityRef as CapabilityRef,
)
from .base_contracts import (
    ContractModel as ContractModel,
)
from .base_contracts import (
    DocumentChunkRepresentation as DocumentChunkRepresentation,
)
from .base_contracts import (
    DocumentContentRepresentation as DocumentContentRepresentation,
)
from .base_contracts import (
    DocumentRepresentation as DocumentRepresentation,
)
from .base_contracts import (
    ErrorCode as ErrorCode,
)
from .base_contracts import (
    ErrorDetail as ErrorDetail,
)
from .base_contracts import (
    ErrorEnvelope as ErrorEnvelope,
)
from .base_contracts import (
    EventAck as EventAck,
)
from .base_contracts import (
    EventEnvelope as EventEnvelope,
)
from .base_contracts import (
    EventSubscription as EventSubscription,
)
from .base_contracts import (
    GameRepresentation as GameRepresentation,
)
from .base_contracts import (
    IntegrityMetadata as IntegrityMetadata,
)
from .base_contracts import (
    ItemT as ItemT,
)
from .base_contracts import (
    JsonValue as JsonValue,
)
from .base_contracts import (
    MediaRepresentation as MediaRepresentation,
)
from .base_contracts import (
    NotificationDeliveryRepresentation as NotificationDeliveryRepresentation,
)
from .base_contracts import (
    NotificationDeliveryResult as NotificationDeliveryResult,
)
from .base_contracts import (
    NotificationProviderRegistration as NotificationProviderRegistration,
)
from .base_contracts import (
    Page as Page,
)
from .base_contracts import (
    Pagination as Pagination,
)
from .base_contracts import (
    PermissionDeclaration as PermissionDeclaration,
)
from .base_contracts import (
    PluginBackendRoute as PluginBackendRoute,
)
from .base_contracts import (
    PluginDependency as PluginDependency,
)
from .base_contracts import (
    PluginFrontendDeclaration as PluginFrontendDeclaration,
)
from .base_contracts import (
    PluginIdentity as PluginIdentity,
)
from .base_contracts import (
    PluginManifest as PluginManifest,
)
from .base_contracts import (
    PluginNativeFrontendDeclaration as PluginNativeFrontendDeclaration,
)
from .base_contracts import (
    PluginPackageIdentity as PluginPackageIdentity,
)
from .base_contracts import (
    PluginPwaDeclaration as PluginPwaDeclaration,
)
from .base_contracts import (
    PluginUiDeclaration as PluginUiDeclaration,
)
from .base_contracts import (
    RequestContext as RequestContext,
)
from .base_contracts import (
    SessionRepresentation as SessionRepresentation,
)
from .base_contracts import (
    StorageEntry as StorageEntry,
)
from .base_contracts import (
    StorageMetadata as StorageMetadata,
)
from .base_contracts import (
    StorageRequirements as StorageRequirements,
)
from .base_contracts import (
    Timestamp as Timestamp,
)
from .base_contracts import (
    UserContext as UserContext,
)
from .base_contracts import (
    UserRepresentation as UserRepresentation,
)
from .base_contracts import (
    VersionNegotiationRequest as VersionNegotiationRequest,
)
from .base_contracts import (
    VersionNegotiationResponse as VersionNegotiationResponse,
)
from .base_contracts import (
    _satisfies_constraint as _satisfies_constraint,
)
from .base_contracts import (
    _validate_range_part as _validate_range_part,
)
from .base_contracts import (
    parse_semver as parse_semver,
)
from .base_contracts import (
    validate_version_range as validate_version_range,
)
from .base_contracts import (
    version_satisfies as version_satisfies,
)
from .frontend_contracts import (
    HostExtensionSlot as HostExtensionSlot,
)
from .frontend_contracts import (
    HostPage as HostPage,
)
from .frontend_contracts import (
    PluginUiDocument as PluginUiDocument,
)
from .frontend_contracts import (
    UiAction as UiAction,
)
from .frontend_contracts import (
    UiContextLocation as UiContextLocation,
)
from .frontend_contracts import (
    UiContextualAction as UiContextualAction,
)
from .frontend_contracts import (
    UiDialog as UiDialog,
)
from .frontend_contracts import (
    UiDialogContribution as UiDialogContribution,
)
from .frontend_contracts import (
    UiDocumentReader as UiDocumentReader,
)
from .frontend_contracts import (
    UiExtension as UiExtension,
)
from .frontend_contracts import (
    UiField as UiField,
)
from .frontend_contracts import (
    UiFieldType as UiFieldType,
)
from .frontend_contracts import (
    UiMenuItem as UiMenuItem,
)
from .frontend_contracts import (
    UiNavigationContribution as UiNavigationContribution,
)
from .frontend_contracts import (
    UiNavigationLocation as UiNavigationLocation,
)
from .frontend_contracts import (
    UiOption as UiOption,
)
from .frontend_contracts import (
    UiOverlayContribution as UiOverlayContribution,
)
from .frontend_contracts import (
    UiPage as UiPage,
)
from .frontend_contracts import (
    UiPageNavigation as UiPageNavigation,
)
from .frontend_contracts import (
    UiPageReplacement as UiPageReplacement,
)
from .frontend_contracts import (
    UiPluginRoute as UiPluginRoute,
)
from .frontend_contracts import (
    UiSchemaVersion as UiSchemaVersion,
)
from .frontend_contracts import (
    UiSettingsContribution as UiSettingsContribution,
)
from .frontend_contracts import (
    UiSettingsSection as UiSettingsSection,
)
from .frontend_contracts import (
    UiTable as UiTable,
)
from .frontend_contracts import (
    UiTableColumn as UiTableColumn,
)
from .frontend_contracts import (
    UiValidation as UiValidation,
)
from .frontend_contracts import (
    UiVisibility as UiVisibility,
)


class CompatibilityStatus(StrEnum):
    """Static compatibility outcome before any plugin code is executed."""

    COMPATIBLE = "compatible"
    INCOMPATIBLE = "incompatible"
    INVALID = "invalid"


class CompatibilityDecision(ContractModel):
    """Actionable result for installation/activation decisions."""

    status: CompatibilityStatus
    reason: str
    action: str


def evaluate_manifest_compatibility(
    manifest: PluginManifest,
    sdk_version: str,
    application_version: str,
) -> CompatibilityDecision:
    """Classify a manifest without executing plugin code."""
    try:
        sdk_ok = version_satisfies(sdk_version, manifest.sdk_version_range)
        app_ok = version_satisfies(application_version, manifest.application_version_range)
    except ValueError as exc:
        return CompatibilityDecision(
            status=CompatibilityStatus.INVALID,
            reason=str(exc),
            action="reject",
        )
    if not sdk_ok:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason="plugin SDK version is outside the declared compatibility range",
            action="quarantine",
        )
    if not app_ok:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason="application version is outside the declared compatibility range",
            action="quarantine",
        )
    return CompatibilityDecision(
        status=CompatibilityStatus.COMPATIBLE,
        reason="manifest is compatible with the current SDK and application",
        action="allow",
    )


def migrate_manifest_data(data: dict[str, Any]) -> dict[str, Any]:
    """Migrate the known legacy manifest shape to manifest version 1.

    This is a pure data migration. It never imports, loads, or executes plugin code.
    Unknown/ambiguous legacy values are rejected rather than guessed.
    """
    migrated = dict(data)
    version = migrated.get("manifest_version", 0)
    if version == 1:
        return migrated
    if version not in {0, None}:
        raise ValueError(f"unsupported manifest version: {version!r}")

    aliases = {
        "id": "plugin_id",
        "display_name": "name",
        "entry_point": "entrypoint",
        "sdk_version": "sdk_version_range",
        "app_version": "application_version_range",
    }
    for old_key, new_key in aliases.items():
        if old_key in migrated:
            if new_key in migrated:
                raise ValueError(f"ambiguous manifest fields: {old_key!r} and {new_key!r}")
            migrated[new_key] = migrated.pop(old_key)

    for key in ("sdk_version_range", "application_version_range"):
        value = migrated.get(key)
        if value is not None and SEMVER_RE.fullmatch(str(value)):
            migrated[key] = f"={value}"

    migrated["manifest_version"] = 1
    return migrated


class DependencyResolutionError(ValueError):
    """Raised when plugin dependencies cannot be resolved safely."""


def resolve_plugin_dependencies(
    manifests: tuple[PluginManifest, ...],
) -> tuple[str, ...]:
    """Return a deterministic dependency-first installation order."""
    by_id = {manifest.plugin_id: manifest for manifest in manifests}
    if len(by_id) != len(manifests):
        raise DependencyResolutionError("duplicate plugin IDs cannot be installed together")

    for manifest in manifests:
        for dependency in manifest.dependencies:
            target = by_id.get(dependency.plugin_id)
            if target is None:
                if dependency.optional:
                    continue
                raise DependencyResolutionError(
                    f"{manifest.plugin_id} requires missing plugin {dependency.plugin_id}"
                )
            if not version_satisfies(target.version, dependency.version_range):
                if dependency.optional:
                    continue
                raise DependencyResolutionError(
                    f"{manifest.plugin_id} requires {dependency.plugin_id} "
                    f"matching {dependency.version_range}, found {target.version}"
                )

    visiting: set[str] = set()
    visited: set[str] = set()
    order: list[str] = []

    def visit(plugin_id: str, path: tuple[str, ...]) -> None:
        if plugin_id in visiting:
            cycle = " -> ".join((*path, plugin_id))
            raise DependencyResolutionError(f"dependency cycle detected: {cycle}")
        if plugin_id in visited:
            return
        visiting.add(plugin_id)
        manifest = by_id[plugin_id]
        dependencies = sorted(
            (
                dependency.plugin_id
                for dependency in manifest.dependencies
                if dependency.plugin_id in by_id
                and not (
                    dependency.optional
                    and not version_satisfies(
                        by_id[dependency.plugin_id].version,
                        dependency.version_range,
                    )
                )
            ),
        )
        for dependency_id in dependencies:
            visit(dependency_id, (*path, plugin_id))
        visiting.remove(plugin_id)
        visited.add(plugin_id)
        order.append(plugin_id)

    for plugin_id in sorted(by_id):
        visit(plugin_id, ())
    return tuple(order)


__all__ = [
    "API_VERSION",
    "ApiVersion",
    "Capability",
    "CapabilityRef",
    "ErrorCode",
    "ErrorDetail",
    "ErrorEnvelope",
    "EventAck",
    "EventEnvelope",
    "EventSubscription",
    "GameRepresentation",
    "JsonValue",
    "MediaRepresentation",
    "DocumentRepresentation",
    "DocumentContentRepresentation",
    "SessionRepresentation",
    "NotificationProviderRegistration",
    "NotificationDeliveryRepresentation",
    "NotificationDeliveryResult",
    "Page",
    "Pagination",
    "PluginIdentity",
    "PluginPackageIdentity",
    "RequestContext",
    "Timestamp",
    "UserContext",
    "UserRepresentation",
    "VersionNegotiationRequest",
    "VersionNegotiationResponse",
    "PermissionDeclaration",
    "PluginDependency",
    "PluginUiDeclaration",
    "StorageRequirements",
    "IntegrityMetadata",
    "PluginManifest",
    "UiSchemaVersion",
    "UiFieldType",
    "UiValidation",
    "UiOption",
    "UiField",
    "UiSettingsSection",
    "UiAction",
    "UiTableColumn",
    "UiTable",
    "UiDialog",
    "UiMenuItem",
    "UiPage",
    "PluginUiDocument",
    "PluginFrontendDeclaration",
    "PluginNativeFrontendDeclaration",
    "PluginPwaDeclaration",
    "BackendRouteAuthorization",
    "BackendRouteMethod",
    "BackendRouteScope",
    "PluginBackendRoute",
    "HostExtensionSlot",
    "HostPage",
    "UiContextLocation",
    "UiContextualAction",
    "UiDialogContribution",
    "UiExtension",
    "UiNavigationContribution",
    "UiNavigationLocation",
    "UiOverlayContribution",
    "UiPageNavigation",
    "UiPageReplacement",
    "UiPluginRoute",
    "UiSettingsContribution",
    "UiVisibility",
    "CompatibilityStatus",
    "CompatibilityDecision",
    "evaluate_manifest_compatibility",
    "migrate_manifest_data",
    "DependencyResolutionError",
    "resolve_plugin_dependencies",
    "parse_semver",
    "validate_version_range",
    "version_satisfies",
]
