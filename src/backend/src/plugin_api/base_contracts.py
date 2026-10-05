"""Core wire types, manifests and semantic version rules for Plugin API v1."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import StrEnum
from typing import Annotated, Any, Generic, Literal, TypeVar, cast
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

API_VERSION = "v1"
PLUGIN_API_CONTRACT_VERSION = "1.1.0"
Timestamp = datetime


class ContractModel(BaseModel):
    """Base model for public wire contracts."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ApiVersion(StrEnum):
    """Major API versions understood by the gateway."""

    V1 = "v1"


class Capability(StrEnum):
    """Stable capability identifiers grouped by capability family."""

    USERS = "users"
    USERS_READ = "users.read"
    USERS_PROFILE_READ = "users.profile.read"
    GAMES = "games"
    GAMES_READ = "games.read"
    GAMES_WRITE = "games.write"
    LIBRARY_LEGACY_READ = "library.legacy.read"
    MEDIA = "media"
    MEDIA_READ = "media.read"
    MEDIA_WRITE = "media.write"
    DOCUMENTS = "documents"
    DOCUMENTS_READ = "documents.read"
    SESSIONS = "sessions"
    SESSIONS_READ = "sessions.read"
    SESSIONS_REVOKE = "sessions.revoke"
    SESSIONS_ADMIN = "sessions.admin"
    NOTIFICATIONS_SEND = "notifications.send"
    NOTIFICATIONS = "notifications"
    NOTIFICATION_PROVIDERS = "notification_providers"
    NOTIFICATION_PROVIDERS_REGISTER = "notification_providers.register"
    NOTIFICATION_PROVIDERS_DELIVER = "notification_providers.deliver"
    EVENTS_SUBSCRIBE = "events.subscribe"
    TASKS_BACKGROUND = "tasks.background"
    SESSIONS_ADMIN_READ = "sessions.admin.read"
    SESSIONS_ADMIN_REVOKE = "sessions.admin.revoke"
    SESSIONS_GEOIP_READ = "sessions.geoip.read"
    SESSIONS_GEOIP_CONFIGURE = "sessions.geoip.configure"
    MEDIA_IMPORT = "media.import"
    PLUGIN_STORAGE = "plugin.storage"
    PLUGIN_SETTINGS = "plugin.settings"
    FRONTEND_NAVIGATION = "frontend.navigation"
    FRONTEND_NAVIGATION_MAIN = "frontend.navigation.main"
    FRONTEND_NAVIGATION_SETTINGS = "frontend.navigation.settings"
    FRONTEND_NAVIGATION_ADMIN = "frontend.navigation.admin"
    FRONTEND_CONTEXT_GAME = "frontend.context.game"
    FRONTEND_CONTEXT_MEDIA = "frontend.context.media"
    FRONTEND_CONTEXT_DOCUMENTS = "frontend.context.documents"
    FRONTEND_SETTINGS = "frontend.settings"
    FRONTEND_PLACEMENT_SIDEBAR = "frontend.placement.sidebar"
    FRONTEND_PLACEMENT_ADMIN = "frontend.placement.settings.admin"
    FRONTEND_PLACEMENT_ACCOUNT = "frontend.placement.settings.account"
    FRONTEND_PLACEMENT_PREFERENCES = "frontend.placement.settings.preferences"
    FRONTEND_OVERLAY = "frontend.overlay"
    FRONTEND_DIALOG = "frontend.dialog"
    FRONTEND_PAGE_EXTEND = "frontend.page.extend"
    FRONTEND_HOME_WIDGETS = "frontend.home.widgets"
    FRONTEND_THEMES = "frontend.themes"
    FRONTEND_PAGE_REPLACE_HOME = "frontend.page.replace.home"
    FRONTEND_PAGE_REPLACE_SETTINGS = "frontend.page.replace.settings"
    FRONTEND_ROUTES = "frontend.routes"
    FRONTEND_NATIVE = "frontend.native"
    FRONTEND_PWA = "frontend.pwa"
    BACKEND_ROUTES = "backend.routes"
    BACKEND_ROUTES_PLUGIN = "backend.routes.plugin"
    BACKEND_ROUTES_HOST = "backend.routes.host"
    NETWORK_OUTBOUND = "network.outbound"
    FULL_API = "api.full"


class CapabilityRef(ContractModel):
    """A capability plus the version of its semantics."""

    name: Capability
    version: int = Field(default=1, ge=1)


class VersionNegotiationRequest(ContractModel):
    """Versions a caller can speak, in preference order."""

    supported_versions: tuple[ApiVersion, ...] = Field(min_length=1)


class VersionNegotiationResponse(ContractModel):
    """Version selected by the gateway."""

    selected_version: ApiVersion
    deprecated: bool = False


class PluginIdentity(ContractModel):
    """Stable identity of an installed plugin."""

    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    installation_id: UUID
    version: str = Field(min_length=1, max_length=64)


class PluginPackageIdentity(ContractModel):
    """Software identity used when deciding whether installation grants may continue."""

    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    publisher_key_id: str | None = Field(default=None, min_length=1, max_length=256)


class UserRepresentation(ContractModel):
    """Stable, non-sensitive user representation for plugin DTOs."""

    id: UUID
    username: str = Field(min_length=1, max_length=255)


class GameRepresentation(ContractModel):
    """Stable game representation exposed by plugin-facing DTOs."""

    id: UUID
    title: str = Field(min_length=1, max_length=512)


class MediaRepresentation(ContractModel):
    """Stable media representation exposed by plugin-facing DTOs."""

    id: UUID
    title: str = Field(min_length=1, max_length=512)
    media_type: str = Field(min_length=1, max_length=64)


class DocumentRepresentation(ContractModel):
    """Safe game-document metadata exposed without host filesystem paths."""

    id: UUID
    game_id: UUID
    game_title: str = Field(min_length=1, max_length=500)
    filename: str = Field(min_length=1, max_length=500)
    media_type: str = Field(min_length=1, max_length=128)
    size_bytes: int = Field(ge=0)
    created_at: int = Field(ge=0)


class DocumentContentRepresentation(ContractModel):
    """Bounded document content encoded for the JSON Plugin API transport."""

    document: DocumentRepresentation
    encoding: str = Field(pattern=r"^base64$")
    content: str = Field(max_length=7_000_000)


class DocumentChunkRepresentation(DocumentContentRepresentation):
    """Additive bounded read transport that fits the runtime action/route limit."""

    content: str = Field(max_length=32_768)
    format: str = Field(pattern=r"^(pdf|text|html|docx|pptx|odt|odp)$")
    offset: int = Field(ge=0)
    next_offset: int = Field(ge=0)
    complete: bool
    content_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SessionRepresentation(ContractModel):
    """Permissioned session metadata; credentials are never exposed."""

    id: UUID
    created_at: int = Field(ge=0)
    expires_at: int = Field(ge=0)
    active: bool
    user_id: UUID | None = None
    username: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    last_seen_at: int | None = Field(default=None, ge=0)
    revoked_at: int | None = Field(default=None, ge=0)
    state: str = Field(default="active", pattern=r"^(active|expired|revoked)$")
    is_current: bool = False
    location: dict[str, str | int | float | None] = Field(default_factory=dict)
    anomaly: dict[str, str | None] = Field(default_factory=dict)


class NotificationProviderRegistration(ContractModel):
    """A plugin-owned provider registered with the core delivery coordinator."""

    provider_id: str = Field(
        min_length=3,
        max_length=128,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )
    name: str = Field(min_length=1, max_length=128)
    action_id: str = Field(
        min_length=1,
        max_length=128,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )


class NotificationDeliveryRepresentation(ContractModel):
    """Minimized delivery work sent from the core coordinator to a provider."""

    notification_id: UUID
    kind: str = Field(min_length=1, max_length=30)
    title: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1, max_length=10_000)
    media_type: str = Field(min_length=1, max_length=32)
    media_id: UUID
    event_at: int = Field(ge=0)


class NotificationDeliveryResult(ContractModel):
    """Provider result interpreted by core-owned retry and terminal-state logic."""

    success: bool
    retryable: bool = False
    error: str | None = Field(default=None, max_length=512)


class UserContext(ContractModel):
    """The minimum authenticated user context carried by a request."""

    user_id: UUID
    authenticated: bool = True


class RequestContext(ContractModel):
    """Identity and authorization context attached to a gateway request."""

    request_id: UUID
    application_id: UUID
    gateway_id: UUID
    plugin: PluginIdentity
    user: UserContext | None = None
    device_id: UUID | None = None
    requested_capability: CapabilityRef


class ErrorCode(StrEnum):
    """Stable machine-readable API error categories."""

    INVALID_REQUEST = "invalid_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    INCOMPATIBLE = "incompatible"
    UNAVAILABLE = "unavailable"
    INTERNAL = "internal"


class ErrorDetail(ContractModel):
    """Safe structured validation/detail information."""

    field: str | None = Field(default=None, max_length=128)
    message: str = Field(min_length=1, max_length=1024)
    code: str | None = Field(default=None, max_length=128)


class ErrorEnvelope(ContractModel):
    """Stable error response without internal exception details."""

    api_version: ApiVersion = ApiVersion.V1
    code: ErrorCode
    message: str = Field(min_length=1, max_length=1024)
    request_id: UUID
    details: tuple[ErrorDetail, ...] = ()


class Pagination(ContractModel):
    """Cursor pagination shared by list endpoints."""

    limit: int = Field(default=50, ge=1, le=200)
    cursor: str | None = Field(default=None, max_length=512)


ItemT = TypeVar("ItemT")


class Page(ContractModel, Generic[ItemT]):
    """A page of stable DTOs without query/database state."""

    items: tuple[ItemT, ...]
    next_cursor: str | None = Field(default=None, max_length=512)


class EventEnvelope(ContractModel, Generic[ItemT]):
    """Versioned event delivered across the plugin boundary."""

    api_version: ApiVersion = ApiVersion.V1
    event_id: UUID
    event_type: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    event_version: int = Field(ge=1)
    occurred_at: Timestamp
    source: str = Field(min_length=1, max_length=128)
    user_id: UUID | None = None
    payload: ItemT

    @field_validator("occurred_at")
    @classmethod
    def require_utc(cls, value: datetime) -> datetime:
        """Require an explicit timezone and normalize it to UTC."""
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("occurred_at must include a timezone")
        return value.astimezone(timezone.utc)


class EventSubscription(ContractModel):
    """Filter for events a plugin is authorized to receive."""

    event_types: tuple[str, ...] = ()
    user_ids: tuple[UUID, ...] = ()
    max_events_per_minute: int = Field(default=60, ge=1, le=10_000)


class EventAck(ContractModel):
    """Acknowledgement of one delivered event."""

    event_id: UUID
    accepted: bool
    error: ErrorEnvelope | None = None


class JsonValue(ContractModel):
    """Explicit wrapper for plugin-owned structured values."""

    value: dict[str, Any]


class StorageEntry(ContractModel):
    """Stable metadata for one plugin-owned storage value."""

    key: str = Field(min_length=1, max_length=255)
    size_bytes: int = Field(ge=0)


class StorageMetadata(ContractModel):
    """Stable plugin storage namespace metadata."""

    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    schema_version: int = Field(ge=1)
    quota_bytes: int = Field(ge=1)
    used_bytes: int = Field(ge=0)


SEMVER_RE = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def parse_semver(value: str) -> tuple[int, int, int]:
    """Parse a strict semantic version."""
    match = SEMVER_RE.fullmatch(value)
    if match is None:
        raise ValueError(f"invalid semantic version: {value!r}")
    major, minor, patch = (int(part) for part in match.groups())
    return major, minor, patch


def _validate_range_part(part: str) -> None:
    """Validate one AND-separated semantic-version range expression."""
    expression = part.strip()
    if expression in {"", "*"}:
        return
    if expression.startswith("^") or expression.startswith("~"):
        parse_semver(expression[1:])
        return
    operator = next((op for op in (">=", "<=", ">", "<", "=") if expression.startswith(op)), "")
    version = expression[len(operator) :] if operator else expression
    if version.endswith((".x", ".*")):
        prefix = version[:-2]
        if prefix and any(not item.isdigit() for item in prefix.split(".")):
            raise ValueError(f"invalid semantic version range: {part!r}")
        if not prefix:
            raise ValueError(f"invalid semantic version range: {part!r}")
        return
    parse_semver(version)


def validate_version_range(value: str) -> str:
    """Validate a deterministic, dependency-safe semantic version range."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("version range must not be empty")
    for part in normalized.split(","):
        _validate_range_part(part)
    return normalized


def _satisfies_constraint(version: tuple[int, int, int], constraint: str) -> bool:
    expression = constraint.strip()
    if expression in {"", "*"}:
        return True
    if expression.startswith("^"):
        lower = parse_semver(expression[1:])
        if lower[0] > 0:
            upper = (lower[0] + 1, 0, 0)
        elif lower[1] > 0:
            upper = (0, lower[1] + 1, 0)
        else:
            upper = (0, 0, lower[2] + 1)
        return lower <= version < upper
    if expression.startswith("~"):
        lower = parse_semver(expression[1:])
        return lower <= version < (lower[0], lower[1] + 1, 0)

    operator = next((op for op in (">=", "<=", ">", "<", "=") if expression.startswith(op)), "")
    value = expression[len(operator) :] if operator else expression
    if value.endswith((".x", ".*")):
        parts = value[:-2].split(".")
        prefix = tuple(int(item) for item in parts)
        return version[: len(prefix)] == prefix
    target = parse_semver(value)
    return {
        "": version == target,
        "=": version == target,
        ">=": version >= target,
        "<=": version <= target,
        ">": version > target,
        "<": version < target,
    }[operator]


def version_satisfies(version: str, version_range: str) -> bool:
    """Return whether a semantic version satisfies every range constraint."""
    parsed = parse_semver(version)
    validate_version_range(version_range)
    return all(_satisfies_constraint(parsed, part) for part in version_range.split(","))


class PermissionDeclaration(ContractModel):
    """A human-readable permission request tied to a capability."""

    capability: CapabilityRef
    rationale: str = Field(min_length=1, max_length=1024)


class PluginDependency(ContractModel):
    """A required or optional dependency on another installed plugin."""

    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    version_range: str
    optional: bool = False

    @field_validator("version_range")
    @classmethod
    def validate_dependency_range(cls, value: str) -> str:
        return validate_version_range(value)


class PluginUiDeclaration(ContractModel):
    """Declarative identifiers exposed to the native frontend."""

    settings: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    pages: tuple[str, ...] = ()
    menus: tuple[str, ...] = ()


class StorageRequirements(ContractModel):
    """Plugin-owned storage requirements; quotas never grant core DB access."""

    quota_mb: int | None = Field(default=None, ge=1, le=1_048_576)


class IntegrityMetadata(ContractModel):
    """Package integrity metadata validated before plugin activation."""

    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    signature: str | None = Field(default=None, min_length=1, max_length=16_384)
    key_id: str | None = Field(default=None, min_length=1, max_length=256)


class PluginFrontendDeclaration(ContractModel):
    """Sandboxed frontend entrypoint bundled inside the plugin package."""

    entry: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_./-]*$",
    )
    inline_assets: bool = Field(default=False, strict=True)


class PluginNativeFrontendDeclaration(ContractModel):
    """Privileged host-native Vue/JavaScript/CSS bundle declaration.

    Merely declaring this bundle never grants native execution. The host only
    serves and activates it for an enabled installation with frontend.native.
    """

    entry: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z0-9][A-Za-z0-9_./-]*$",
    )
    styles: tuple[str, ...] = ()

    @field_validator("entry")
    @classmethod
    def validate_entry(cls, value: str) -> str:
        if not value.startswith("native/"):
            raise ValueError("native frontend entry must be under native/")
        return value

    @field_validator("styles")
    @classmethod
    def validate_styles(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        for value in values:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_./-]*", value):
                raise ValueError("native frontend styles contain an invalid path")
            if not value.startswith("native/") or ".." in value.split("/"):
                raise ValueError("native frontend styles must be under native/")
        if len(values) != len(set(values)):
            raise ValueError("native frontend styles cannot contain duplicates")
        return values


class BackendRouteScope(StrEnum):
    """Host-owned URL areas available to a declared plugin route."""

    PLUGIN = "plugin"
    HOST = "host"


class BackendRouteAuthorization(StrEnum):
    """Authentication policy enforced by the host before plugin execution."""

    AUTHENTICATED = "authenticated"
    ADMIN = "admin"


class BackendRouteMethod(StrEnum):
    """HTTP methods supported by the bounded plugin route transport."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class PluginBackendRoute(ContractModel):
    """A statically declared backend handler mounted and mediated by the host."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    scope: BackendRouteScope = BackendRouteScope.PLUGIN
    path: str = Field(min_length=1, max_length=255)
    methods: tuple[BackendRouteMethod, ...] = (BackendRouteMethod.GET,)
    handler: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*(?::[A-Za-z_][A-Za-z0-9_]*)?$",
    )
    authorization: BackendRouteAuthorization = BackendRouteAuthorization.AUTHENTICATED

    @field_validator("path")
    @classmethod
    def validate_path(cls, value: str) -> str:
        """Reject catch-all, traversal, and otherwise ambiguous route segments."""

        segment_pattern = r"[a-z0-9][a-z0-9._-]*|\{[a-z_][a-z0-9_]*\}"
        parts = (
            value.removeprefix("/api/").split("/") if value.startswith("/") else value.split("/")
        )
        if not parts or any(not re.fullmatch(segment_pattern, part) for part in parts):
            raise ValueError("backend route path contains an invalid segment")
        parameters = [part for part in parts if part.startswith("{")]
        if len(parameters) != len(set(parameters)):
            raise ValueError("backend route path contains duplicate parameters")
        return value.rstrip("/")

    @field_validator("methods")
    @classmethod
    def validate_methods(
        cls, values: tuple[BackendRouteMethod, ...]
    ) -> tuple[BackendRouteMethod, ...]:
        """Require a non-empty set of supported, unique HTTP methods."""

        if not values:
            raise ValueError("backend route must declare at least one method")
        if len(values) != len(set(values)):
            raise ValueError("backend route methods cannot contain duplicates")
        return values

    @model_validator(mode="after")
    def validate_scope_path(self) -> "PluginBackendRoute":
        """Apply namespace-specific ownership rules to the declared path."""

        scope = cast(BackendRouteScope, self.scope)
        path = cast(str, self.path)
        # Pydantic fields are runtime values; pylint otherwise treats ``path`` as FieldInfo.
        # pylint: disable=no-member
        if scope is BackendRouteScope.PLUGIN and path.startswith("/"):
            raise ValueError("namespaced backend route paths must be relative")
        reserved_plugin_roots = {
            "actions",
            "changelog",
            "capabilities",
            "disable",
            "enable",
            "frontend",
            "logs",
            "native-frontend",
            "permissions",
            "retry",
            "reinstall",
            "rollback",
            "history",
            "start",
            "stop",
            "auto-update",
            "detail",
            "secrets",
            "settings",
            "ui",
            "update",
        }
        if scope is BackendRouteScope.PLUGIN and path.split("/", 1)[0] in reserved_plugin_roots:
            raise ValueError("namespaced backend route conflicts with a host-owned plugin path")
        if scope is BackendRouteScope.HOST and not path.startswith("/api/"):
            raise ValueError("host backend route paths must start with /api/")
        if scope is BackendRouteScope.HOST and path.startswith("/api/plugins/"):
            raise ValueError("host backend routes cannot claim the plugin management namespace")
        # pylint: enable=no-member
        return self


class PluginPwaDeclaration(ContractModel):
    """Non-executable install metadata; the host owns the worker and root routes."""

    name: str = Field(min_length=1, max_length=128)
    short_name: str = Field(min_length=1, max_length=32)
    theme_color: str = Field(default="#0f1117", pattern=r"^#[0-9a-fA-F]{6}$")
    background_color: str = Field(default="#0f1117", pattern=r"^#[0-9a-fA-F]{6}$")
    manifest: str = Field(
        default="pwa/manifest.webmanifest", pattern=r"^pwa/manifest\.webmanifest$"
    )
    icons: tuple[str, str] = ("pwa/icon-192.png", "pwa/icon-512.png")

    @field_validator("icons")
    @classmethod
    def validate_icons(cls, values: tuple[str, str]) -> tuple[str, str]:
        if values != ("pwa/icon-192.png", "pwa/icon-512.png"):
            raise ValueError("PWA v1 requires the two bounded PNG icons")
        return values


class PluginManifest(ContractModel):
    """Static plugin manifest validated without importing or executing the plugin."""

    manifest_version: int = Field(default=1, ge=1, le=1)
    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    name: str = Field(min_length=1, max_length=128)
    version: str
    # Missing declarations remain legacy; ranges must never imply UI/API migration.
    api_contract_version: str = "1.0.0"
    description: str = Field(default="", max_length=2_000)
    icon: str | None = Field(default=None, max_length=2048)
    tags: tuple[str, ...] = ()
    automatic_update: bool = True
    entrypoint: str = Field(
        min_length=1,
        max_length=255,
        pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*(?::[A-Za-z_][A-Za-z0-9_]*)?$",
    )
    sdk_version_range: str
    application_version_range: str
    capabilities: tuple[CapabilityRef, ...] = ()
    permissions: tuple[PermissionDeclaration, ...] = ()
    dependencies: tuple[PluginDependency, ...] = ()
    ui: PluginUiDeclaration = PluginUiDeclaration()
    storage: StorageRequirements = StorageRequirements()
    integrity: IntegrityMetadata
    frontend: PluginFrontendDeclaration | None = None
    native_frontend: PluginNativeFrontendDeclaration | None = None
    backend_routes: tuple[PluginBackendRoute, ...] = ()
    pwa: PluginPwaDeclaration | None = None

    @field_validator("version", "api_contract_version")
    @classmethod
    def validate_plugin_version(cls, value: str) -> str:
        parse_semver(value)
        return value

    @field_validator("sdk_version_range", "application_version_range")
    @classmethod
    def validate_compatibility_range(cls, value: str) -> str:
        return validate_version_range(value)

    @model_validator(mode="after")
    def validate_unique_declarations(self) -> "PluginManifest":
        dependency_ids = [dependency.plugin_id for dependency in self.dependencies]
        if len(dependency_ids) != len(set(dependency_ids)):
            raise ValueError("manifest contains duplicate dependency declarations")
        capability_names = [capability.name for capability in self.capabilities]
        if len(capability_names) != len(set(capability_names)):
            raise ValueError("manifest contains duplicate capability declarations")
        permission_names = [permission.capability.name for permission in self.permissions]
        if len(permission_names) != len(set(permission_names)):
            raise ValueError("manifest contains duplicate permission declarations")
        capability_versions = {
            capability.name: capability.version for capability in self.capabilities
        }
        for permission in self.permissions:
            declared_version = capability_versions.get(permission.capability.name)
            if declared_version is None or declared_version != permission.capability.version:
                raise ValueError(
                    f"permission {permission.capability.name.value} v{permission.capability.version} "
                    "is not declared by the plugin"
                )
        if self.native_frontend is not None and Capability.FRONTEND_NATIVE not in capability_names:
            raise ValueError("native_frontend requires the frontend.native capability")
        if self.pwa is not None and not any(
            permission.capability == CapabilityRef(name=Capability.FRONTEND_PWA)
            for permission in self.permissions
        ):
            raise ValueError("pwa requires an explicit frontend.pwa v1 permission")
        route_ids = [route.id for route in self.backend_routes]
        if len(route_ids) != len(set(route_ids)):
            raise ValueError("manifest contains duplicate backend route declarations")
        route_owners: list[tuple[BackendRouteScope, str, BackendRouteMethod]] = []
        for route in self.backend_routes:
            required = (
                Capability.BACKEND_ROUTES_PLUGIN
                if route.scope is BackendRouteScope.PLUGIN
                else Capability.BACKEND_ROUTES_HOST
            )
            if not {
                required,
                Capability.BACKEND_ROUTES,
                Capability.FULL_API,
            }.intersection(capability_names):
                raise ValueError(f"backend route {route.id} requires {required.value}")
            for method in route.methods:
                route_parts = route.path.split("/")
                for owner_scope, owner_path, owner_method in route_owners:
                    owner_parts = owner_path.split("/")
                    overlaps = len(route_parts) == len(owner_parts) and all(
                        left == right or left.startswith("{") or right.startswith("{")
                        for left, right in zip(route_parts, owner_parts, strict=True)
                    )
                    if route.scope is owner_scope and method is owner_method and overlaps:
                        raise ValueError("manifest contains conflicting backend routes")
                route_owners.append((route.scope, route.path, method))
        return self
