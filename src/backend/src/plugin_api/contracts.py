"""Stable public Plugin API contract exports and compatibility decisions.

Core and frontend models have separate owners; consumers continue importing
this facade so the versioned API and schema references remain unchanged.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base_contracts import (
    API_VERSION as API_VERSION,
)
from .base_contracts import (
    PLUGIN_API_CONTRACT_VERSION as PLUGIN_API_CONTRACT_VERSION,
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
    PluginScheduledTask as PluginScheduledTask,
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
from .ui_contracts import (
    HostExtensionSlot as HostExtensionSlot,
)
from .ui_contracts import (
    HostPage as HostPage,
)
from .ui_contracts import (
    PluginUiDocument as PluginUiDocument,
)
from .ui_contracts import (
    ThemeColor as ThemeColor,
)
from .ui_contracts import (
    UiAction as UiAction,
)
from .ui_contracts import (
    UiContextLocation as UiContextLocation,
)
from .ui_contracts import (
    UiContextualAction as UiContextualAction,
)
from .ui_contracts import (
    UiDialog as UiDialog,
)
from .ui_contracts import (
    UiDialogContribution as UiDialogContribution,
)
from .ui_contracts import (
    UiDocumentReader as UiDocumentReader,
)
from .ui_contracts import (
    UiExtension as UiExtension,
)
from .ui_contracts import (
    UiField as UiField,
)
from .ui_contracts import (
    UiFieldType as UiFieldType,
)
from .ui_contracts import (
    UiHomeWidget as UiHomeWidget,
)
from .ui_contracts import (
    UiMenuItem as UiMenuItem,
)
from .ui_contracts import (
    UiNavigationContribution as UiNavigationContribution,
)
from .ui_contracts import (
    UiNavigationLocation as UiNavigationLocation,
)
from .ui_contracts import (
    UiOption as UiOption,
)
from .ui_contracts import (
    UiOverlayContribution as UiOverlayContribution,
)
from .ui_contracts import (
    UiPage as UiPage,
)
from .ui_contracts import (
    UiPageNavigation as UiPageNavigation,
)
from .ui_contracts import (
    UiPageReplacement as UiPageReplacement,
)
from .ui_contracts import (
    UiPlacement as UiPlacement,
)
from .ui_contracts import (
    UiPluginRoute as UiPluginRoute,
)
from .ui_contracts import (
    UiSchemaVersion as UiSchemaVersion,
)
from .ui_contracts import (
    UiSettingsContribution as UiSettingsContribution,
)
from .ui_contracts import (
    UiSettingsSection as UiSettingsSection,
)
from .ui_contracts import UiShortcut as UiShortcut
from .ui_contracts import (
    UiTable as UiTable,
)
from .ui_contracts import (
    UiTableColumn as UiTableColumn,
)
from .ui_contracts import (
    UiTheme as UiTheme,
)
from .ui_contracts import (
    UiThemeColors as UiThemeColors,
)
from .ui_contracts import (
    UiThemePalette as UiThemePalette,
)
from .ui_contracts import (
    UiValidation as UiValidation,
)
from .ui_contracts import (
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


def evaluate_manifest_compatibility(
    manifest: PluginManifest,
    sdk_version: str,
    application_version: str,
    *,
    allow_legacy: bool | None = None,
) -> CompatibilityDecision:
    """Classify a manifest without executing plugin code."""
    from .compatibility import legacy_plugin_allowed, manifest_compatibility_checks

    try:
        checks = manifest_compatibility_checks(
            manifest,
            sdk_version,
            application_version,
            allow_legacy=legacy_plugin_allowed(manifest.plugin_id)
            if allow_legacy is None
            else allow_legacy,
        )
    except ValueError as exc:
        return CompatibilityDecision(
            status=CompatibilityStatus.INVALID,
            reason=str(exc),
            action="reject",
        )
    failures = [item["reason"] for item in checks if item["status"] == "incompatible"]
    if failures:
        return CompatibilityDecision(
            status=CompatibilityStatus.INCOMPATIBLE,
            reason=" ".join(failures),
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
    "PluginScheduledTask",
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
    "UiShortcut",
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
