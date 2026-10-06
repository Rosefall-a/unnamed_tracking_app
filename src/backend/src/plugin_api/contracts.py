"""Stable public Plugin API contract exports and compatibility decisions.

Core and frontend models have separate owners; consumers continue importing
this facade so the versioned API and schema references remain unchanged.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from .base_contracts import (
    API_VERSION,
    PLUGIN_API_CONTRACT_VERSION,
    SEMVER_RE,
    ApiVersion,
    BackendRouteAuthorization,
    BackendRouteMethod,
    BackendRouteScope,
    Capability,
    CapabilityRef,
    ContractModel,
    DocumentChunkRepresentation,
    DocumentContentRepresentation,
    DocumentRepresentation,
    ErrorCode,
    ErrorDetail,
    ErrorEnvelope,
    EventAck,
    EventEnvelope,
    EventSubscription,
    GameRepresentation,
    IntegrityMetadata,
    ItemT,
    JsonValue,
    MediaRepresentation,
    NotificationDeliveryRepresentation,
    NotificationDeliveryResult,
    NotificationProviderRegistration,
    Page,
    Pagination,
    PermissionDeclaration,
    PluginBackendRoute,
    PluginDependency,
    PluginFrontendDeclaration,
    PluginIdentity,
    PluginManifest,
    PluginNativeFrontendDeclaration,
    PluginPackageIdentity,
    PluginPwaDeclaration,
    PluginScheduledTask,
    PluginUiDeclaration,
    RequestContext,
    SessionRepresentation,
    StorageEntry,
    StorageMetadata,
    StorageRequirements,
    Timestamp,
    UserContext,
    UserRepresentation,
    VersionNegotiationRequest,
    VersionNegotiationResponse,
    parse_semver,
    validate_version_range,
    version_satisfies,
)
from .compatibility import (
    legacy_plugin_allowed,
    manifest_compatibility_checks,
    plugin_contract_compatibility_reason,
)
from .ui_contracts import (
    HostExtensionSlot,
    HostPage,
    PluginUiDocument,
    ThemeColor,
    UiAction,
    UiContextLocation,
    UiContextualAction,
    UiDialog,
    UiDialogContribution,
    UiDocumentReader,
    UiExtension,
    UiField,
    UiFieldType,
    UiHomeWidget,
    UiMenuItem,
    UiNavigationContribution,
    UiNavigationLocation,
    UiOption,
    UiOverlayContribution,
    UiPage,
    UiPageNavigation,
    UiPageReplacement,
    UiPlacement,
    UiPluginRoute,
    UiSchemaVersion,
    UiSettingsContribution,
    UiSettingsSection,
    UiShortcut,
    UiTable,
    UiTableColumn,
    UiTheme,
    UiThemeColors,
    UiThemePalette,
    UiValidation,
    UiVisibility,
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
    *,
    allow_legacy: bool | None = None,
) -> CompatibilityDecision:
    """Classify a manifest without executing plugin code."""
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
    "DocumentChunkRepresentation",
    "ItemT",
    "StorageEntry",
    "StorageMetadata",
    "ThemeColor",
    "UiDocumentReader",
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
