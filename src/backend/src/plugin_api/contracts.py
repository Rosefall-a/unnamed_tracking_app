"""Stable public Plugin API contract exports and compatibility decisions.

Core and frontend models have separate owners; consumers continue importing
this facade so the versioned API and schema references remain unchanged.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base_contracts import (
    API_VERSION as API_VERSION,
    ApiVersion as ApiVersion,
    BackendRouteAuthorization as BackendRouteAuthorization,
    BackendRouteMethod as BackendRouteMethod,
    BackendRouteScope as BackendRouteScope,
    Capability as Capability,
    CapabilityRef as CapabilityRef,
    ContractModel as ContractModel,
    DocumentChunkRepresentation as DocumentChunkRepresentation,
    DocumentContentRepresentation as DocumentContentRepresentation,
    DocumentRepresentation as DocumentRepresentation,
    ErrorCode as ErrorCode,
    ErrorDetail as ErrorDetail,
    ErrorEnvelope as ErrorEnvelope,
    EventAck as EventAck,
    EventEnvelope as EventEnvelope,
    EventSubscription as EventSubscription,
    GameRepresentation as GameRepresentation,
    IntegrityMetadata as IntegrityMetadata,
    ItemT as ItemT,
    JsonValue as JsonValue,
    MediaRepresentation as MediaRepresentation,
    NotificationDeliveryRepresentation as NotificationDeliveryRepresentation,
    NotificationDeliveryResult as NotificationDeliveryResult,
    NotificationProviderRegistration as NotificationProviderRegistration,
    PLUGIN_API_CONTRACT_VERSION as PLUGIN_API_CONTRACT_VERSION,
    Page as Page,
    Pagination as Pagination,
    PermissionDeclaration as PermissionDeclaration,
    PluginBackendRoute as PluginBackendRoute,
    PluginDependency as PluginDependency,
    PluginFrontendDeclaration as PluginFrontendDeclaration,
    PluginIdentity as PluginIdentity,
    PluginManifest as PluginManifest,
    PluginNativeFrontendDeclaration as PluginNativeFrontendDeclaration,
    PluginPackageIdentity as PluginPackageIdentity,
    PluginPwaDeclaration as PluginPwaDeclaration,
    PluginUiDeclaration as PluginUiDeclaration,
    RequestContext as RequestContext,
    SEMVER_RE as SEMVER_RE,
    SessionRepresentation as SessionRepresentation,
    StorageEntry as StorageEntry,
    StorageMetadata as StorageMetadata,
    StorageRequirements as StorageRequirements,
    Timestamp as Timestamp,
    UserContext as UserContext,
    UserRepresentation as UserRepresentation,
    VersionNegotiationRequest as VersionNegotiationRequest,
    VersionNegotiationResponse as VersionNegotiationResponse,
    _satisfies_constraint as _satisfies_constraint,
    _validate_range_part as _validate_range_part,
    parse_semver as parse_semver,
    validate_version_range as validate_version_range,
    version_satisfies as version_satisfies,
)
from .ui_contracts import (
    UiPlacement as UiPlacement,
    HostExtensionSlot as HostExtensionSlot,
    HostPage as HostPage,
    PluginUiDocument as PluginUiDocument,
    ThemeColor as ThemeColor,
    UiAction as UiAction,
    UiContextLocation as UiContextLocation,
    UiContextualAction as UiContextualAction,
    UiDialog as UiDialog,
    UiDialogContribution as UiDialogContribution,
    UiDocumentReader as UiDocumentReader,
    UiExtension as UiExtension,
    UiField as UiField,
    UiFieldType as UiFieldType,
    UiHomeWidget as UiHomeWidget,
    UiMenuItem as UiMenuItem,
    UiNavigationContribution as UiNavigationContribution,
    UiNavigationLocation as UiNavigationLocation,
    UiOption as UiOption,
    UiOverlayContribution as UiOverlayContribution,
    UiPage as UiPage,
    UiPageNavigation as UiPageNavigation,
    UiPageReplacement as UiPageReplacement,
    UiPluginRoute as UiPluginRoute,
    UiSchemaVersion as UiSchemaVersion,
    UiSettingsContribution as UiSettingsContribution,
    UiSettingsSection as UiSettingsSection,
    UiTable as UiTable,
    UiTableColumn as UiTableColumn,
    UiTheme as UiTheme,
    UiThemeColors as UiThemeColors,
    UiThemePalette as UiThemePalette,
    UiValidation as UiValidation,
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


def plugin_contract_compatibility_reason(
    declared_version: str, host_version: str = PLUGIN_API_CONTRACT_VERSION
) -> str | None:
    """Require an explicit migration across the v1.0 to v1.1 platform boundary."""
    declared = parse_semver(declared_version)
    host = parse_semver(host_version)
    if host >= (1, 1, 0) and declared < (1, 1, 0):
        return (
            f"Plugin API contract {declared_version} is v1.0-only. "
            f"This host requires v1.1.0 or a later compatible contract ({host_version}); "
            "the whole plugin is stopped until a verified migrated update is installed."
        )
    if declared[0] != host[0] or declared > host:
        return f"Plugin API contract {declared_version} is not supported by this host ({host_version})."
    return None


def evaluate_manifest_compatibility(
    manifest: PluginManifest,
    sdk_version: str,
    application_version: str,
) -> CompatibilityDecision:
    """Classify a manifest without executing plugin code."""
    try:
        contract_error = plugin_contract_compatibility_reason(
            manifest.api_contract_version, sdk_version
        )
        sdk_ok = version_satisfies(sdk_version, manifest.sdk_version_range)
        app_ok = version_satisfies(application_version, manifest.application_version_range)
    except ValueError as exc:
        return CompatibilityDecision(
            status=CompatibilityStatus.INVALID,
            reason=str(exc),
            action="reject",
        )
    if contract_error:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=contract_error,
            action="quarantine",
        )
    if not sdk_ok:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=(
                f"Host plugin SDK {sdk_version} is outside this plugin's required range "
                f"({manifest.sdk_version_range}). Choose a verified compatible plugin release "
                "or update the host and plugin runtime together."
            ),
            action="quarantine",
        )
    if not app_ok:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=(
                f"Host application compatibility version {application_version} is outside this "
                f"plugin's required range ({manifest.application_version_range}). "
                "Update the application or choose a verified release supporting this host."
            ),
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
    "PLUGIN_API_CONTRACT_VERSION",
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
    "UiPlacement",
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
    "UiHomeWidget",
    "UiTheme",
    "UiThemeColors",
    "UiThemePalette",
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
    "plugin_contract_compatibility_reason",
    "migrate_manifest_data",
    "DependencyResolutionError",
    "resolve_plugin_dependencies",
    "parse_semver",
    "validate_version_range",
    "version_satisfies",
]
