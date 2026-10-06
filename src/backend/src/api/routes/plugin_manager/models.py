"""Validated HTTP request and catalogue response models for Plugin Manager."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.plugin_api.contracts import PluginDependency


class PluginSettingsIn(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)


class PluginActionContext(BaseModel):
    """Host context accepted from a contribution mount, never arbitrary plugin data."""

    model_config = ConfigDict(extra="forbid")

    kind: str = Field(pattern=r"^(game|media|documents)$")
    resource_id: str = Field(min_length=1, max_length=128)
    resource_type: str | None = Field(default=None, min_length=1, max_length=64)


class PluginActionIn(PluginSettingsIn):
    confirmed: bool = Field(default=False, strict=True)
    context: PluginActionContext | None = None


class PluginInstallUrl(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    expected_digest: str | None = Field(default=None, min_length=64, max_length=64)
    source_type: str = Field(default="url", pattern=r"^(url|catalogue)$")
    catalogue_url: str | None = Field(default=None, max_length=2048)
    release_notes: str | None = Field(default=None, max_length=4_000)
    changelog_url: str | None = Field(default=None, max_length=2048)
    admin_password: str | None = Field(default=None, min_length=1, max_length=1024)
    confirm_dangerous: bool = False


class CatalogueIcon(BaseModel):
    path: str = Field(min_length=1, max_length=255)
    sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")

    @model_validator(mode="after")
    def safe_path(self) -> "CatalogueIcon":
        if (
            "\\" in self.path
            or self.path.startswith("/")
            or any(part in {"", ".", ".."} for part in self.path.split("/"))
        ):
            raise ValueError("Icon path must be a safe relative package path")
        return self


class PluginCatalogEntry(BaseModel):
    """Transport metadata; packaged assets are validated during catalogue normalization."""

    model_config = {"populate_by_name": True}
    plugin_id: str = Field(min_length=1, max_length=128)
    name: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2_000)
    version: str = Field(min_length=1, max_length=64)
    url: str = Field(min_length=1, max_length=2048)
    release_notes: str | None = Field(default=None, max_length=4_000)
    changelog_url: str | None = Field(default=None, max_length=2048)
    dependencies: tuple[PluginDependency, ...] = ()
    icon: str | dict[str, str] | None = None
    icon_metadata: dict[str, str] | None = None
    publisher: str | None = None
    tags: tuple[str, ...] = ()
    readme: str | None = None
    compatibility: str | None = None
    permissions: list[dict[str, object]] = Field(default_factory=list)
    digest: str | None = Field(
        default=None,
        alias="sha256",
        pattern=r"^[0-9a-fA-F]{64}$",
    )
    package_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    package: dict[str, object] = Field(default_factory=dict)
    signing: dict[str, object] = Field(default_factory=dict)
    documentation: dict[str, object] = Field(default_factory=dict)
    build: dict[str, object] = Field(default_factory=dict)
    automatic_update: bool = True


class PluginBackendRouteResponse(BaseModel):
    """Bounded JSON response returned by an isolated backend route handler."""

    model_config = ConfigDict(extra="forbid")

    status_code: int = Field(default=200, ge=200, le=599)
    body: Any = None


class PluginCatalogueCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    url: str = Field(min_length=1, max_length=2048)
    enabled: bool = True
    priority: int = Field(default=100, ge=1, le=10_000)


class PluginCatalogueUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=128)
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    enabled: bool | None = None
    priority: int | None = Field(default=None, ge=0, le=10_000)


class ManagerSettingsIn(BaseModel):
    """Host-owned manager policy; approval identity is recorded by the server."""

    model_config = ConfigDict(extra="forbid")
    automatic_updates: bool | None = None
    retained_versions: int | None = Field(default=None, ge=1, le=100)
    reduced_isolation_acknowledged: bool | None = Field(default=None, strict=True)


class AutoUpdateIn(BaseModel):
    mode: str = Field(pattern=r"^(follow|enabled|disabled)$")


class PackageOperationIn(BaseModel):
    """Explicit lifecycle decisions bound to the reviewed package payload."""

    expected_digest: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    approved_permissions: list[str] = Field(default_factory=list)
    permissions_reviewed: bool = Field(default=False, strict=True)
    allow_untrusted: bool = False
    confirm_dangerous: bool = False
    admin_password: str | None = None
    purge: bool = False
    confirmed: bool = False
    history_id: UUID | None = None


class ManagementTokenIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str]


class PluginGatewayIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: str = Field(default="v1", min_length=1, max_length=16)
    plugin_id: str
    installation_id: UUID
    request_id: UUID
    user_id: UUID
    method: str
    capability: str
    capability_version: int = Field(default=1, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)
