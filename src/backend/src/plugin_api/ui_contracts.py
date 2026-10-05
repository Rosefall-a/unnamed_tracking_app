"""Declarative frontend wire contracts, independent of host rendering."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Literal, cast

from pydantic import Field, field_validator, model_validator

from .base_contracts import (
    CapabilityRef,
    ContractModel,
    PluginFrontendDeclaration,
    PluginNativeFrontendDeclaration,
    parse_semver,
)


class UiSchemaVersion(StrEnum):
    """Versioned declarative UI schema semantics."""

    V1 = "v1"


class UiFieldType(StrEnum):
    """Native field controls supported by the v1 renderer."""

    TEXT = "text"
    TEXTAREA = "textarea"
    PASSWORD = "password"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    MULTISELECT = "multiselect"


class UiValidation(ContractModel):
    """Safe client/server validation constraints for a declarative field."""

    pattern: str | None = Field(default=None, max_length=256)
    min_length: int | None = Field(default=None, ge=0, le=10_000)
    max_length: int | None = Field(default=None, ge=0, le=10_000)
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def validate_bounds(self) -> "UiValidation":
        if (
            self.min_length is not None
            and self.max_length is not None
            and self.min_length > self.max_length
        ):
            raise ValueError("min_length cannot exceed max_length")
        if self.minimum is not None and self.maximum is not None and self.minimum > self.maximum:
            raise ValueError("minimum cannot exceed maximum")
        if self.pattern is not None:
            try:
                re.compile(self.pattern)
            except re.error as exc:
                raise ValueError("pattern must be a valid regular expression") from exc
        return self


class UiOption(ContractModel):
    """A non-executable option rendered by a select control."""

    value: str = Field(min_length=1, max_length=256)
    label: str = Field(min_length=1, max_length=256)


class UiField(ContractModel):
    """One declarative settings value; secrets are write-only at the host boundary."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=256)
    type: UiFieldType
    description: str = Field(default="", max_length=2_000)
    required: bool = False
    secret: bool = False
    default: str | int | float | bool | tuple[str, ...] | None = None
    options: tuple[UiOption, ...] = ()
    validation: UiValidation | None = None

    @model_validator(mode="after")
    def validate_options(self) -> "UiField":
        if self.type in {UiFieldType.SELECT, UiFieldType.MULTISELECT} and not self.options:
            raise ValueError("select fields require options")
        if self.type not in {UiFieldType.SELECT, UiFieldType.MULTISELECT} and self.options:
            raise ValueError("only select fields may declare options")
        option_values = [option.value for option in self.options]
        if len(option_values) != len(set(option_values)):
            raise ValueError("select fields cannot contain duplicate option values")
        if self.type is UiFieldType.PASSWORD and not self.secret:
            raise ValueError("password fields must be marked secret")
        if self.secret and self.default is not None:
            raise ValueError("secret fields cannot expose default values")
        if self.default is not None:
            expected = {
                UiFieldType.TEXT: (str,),
                UiFieldType.TEXTAREA: (str,),
                UiFieldType.PASSWORD: (str,),
                UiFieldType.NUMBER: (int, float),
                UiFieldType.BOOLEAN: (bool,),
                UiFieldType.SELECT: (str,),
                UiFieldType.MULTISELECT: (tuple,),
            }[self.type]
            if self.type is UiFieldType.NUMBER:
                valid_number = isinstance(self.default, (int, float)) and not isinstance(
                    self.default, bool
                )
                if not valid_number:
                    raise ValueError(f"default value does not match field type {self.type.value}")
            elif not isinstance(self.default, expected):
                raise ValueError(f"default value does not match field type {self.type.value}")
            if self.type is UiFieldType.MULTISELECT:
                default_values = cast(tuple[str, ...], self.default)
                if not all(isinstance(value, str) for value in default_values):
                    raise ValueError("multiselect defaults must contain only strings")
                if any(value not in option_values for value in default_values):
                    raise ValueError("default value must use declared options")
            elif self.type is UiFieldType.SELECT:
                default_value = cast(str, self.default)
                if default_value not in option_values:
                    raise ValueError("default value must use declared options")
        return self


class UiSettingsSection(ContractModel):
    """A declarative group of settings fields."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2_000)
    fields: tuple[UiField, ...] = ()

    @model_validator(mode="after")
    def validate_unique_fields(self) -> "UiSettingsSection":
        ids = [field.id for field in self.fields]
        if len(ids) != len(set(ids)):
            raise ValueError("settings section contains duplicate field IDs")
        return self


class UiAction(ContractModel):
    """A declarative action dispatched through the authenticated gateway."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=256)
    handler: str | None = Field(
        default=None,
        max_length=255,
        pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*(?::[A-Za-z_][A-Za-z0-9_]*)?$",
    )
    capability: CapabilityRef | None = None
    confirmation: str | None = Field(default=None, max_length=512)
    external_navigation: bool = False


class UiTableColumn(ContractModel):
    """A table column mapped to a response property, never executable code."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=256)


class UiTable(ContractModel):
    """A declarative read-only table."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=256)
    columns: tuple[UiTableColumn, ...] = ()
    empty_message: str = Field(default="No data available.", max_length=512)


class UiDialog(ContractModel):
    """A declarative dialog whose actions still execute through the gateway."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=256)
    body: str = Field(default="", max_length=4_000)
    actions: tuple[str, ...] = ()


class UiMenuItem(ContractModel):
    """A native navigation item; arbitrary external URLs are not supported."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=256)
    page_id: str | None = None
    action_id: str | None = None

    @model_validator(mode="after")
    def require_target(self) -> "UiMenuItem":
        if (self.page_id is None) == (self.action_id is None):
            raise ValueError("menu item must target exactly one page or action")
        return self


class HostExtensionSlot(StrEnum):
    """Host-owned locations that accept declarative plugin contributions."""

    HOME_AFTER_WIDGETS = "home.after-widgets"
    GAME_OVERVIEW_AFTER_HEADER = "game.overview.after-header"
    GAME_DOCUMENTS_ACTIONS = "game.documents.actions"
    MEDIA_DETAIL_AFTER_HEADER = "media.detail.after-header"
    APP_GLOBAL = "app.global"
    HOME_REPLACE = "home.replace"


class UiNavigationLocation(StrEnum):
    """Host-owned navigation locations available to plugin contributions."""

    MAIN_SIDEBAR = "main.sidebar"
    SETTINGS_SIDEBAR = "settings.sidebar"
    ADMINISTRATION = "administration"
    GAME_CONTEXT = "game.context"
    MEDIA_CONTEXT = "media.context"


class UiContextLocation(StrEnum):
    """Host contexts that can expose a plugin action."""

    GAME = "game"
    MEDIA = "media"
    DOCUMENTS = "documents"


class HostPage(StrEnum):
    """Host pages with explicit page-scoped replacement permissions."""

    HOME = "home"
    SETTINGS = "settings"


class UiVisibility(ContractModel):
    """Host-evaluated visibility conditions; plugins cannot evaluate code here."""

    admin_only: bool = False


class UiPageNavigation(ContractModel):
    """Optional host navigation metadata for a native plugin page."""

    sidebar: bool = False
    label: str | None = Field(default=None, min_length=1, max_length=64)
    order: int = Field(default=0, ge=-1_000, le=1_000)


class UiPage(ContractModel):
    """A native plugin page composed only from approved declarative primitives."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=256)
    description: str = Field(default="", max_length=2_000)
    settings: tuple[str, ...] = ()
    actions: tuple[str, ...] = ()
    tables: tuple[str, ...] = ()
    dialogs: tuple[str, ...] = ()
    navigation: UiPageNavigation | None = None


class UiExtension(ContractModel):
    """A native plugin page mounted into one allowlisted host extension slot."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    slot: HostExtensionSlot
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    order: int = Field(default=0, ge=-1_000, le=1_000)


class UiHomeWidget(ContractModel):
    """Account-selected Home content with optional phone layout and personal options."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    mobile_page_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    order: int = Field(default=0, ge=-1_000, le=1_000)
    configuration: tuple[UiField, ...] = Field(default=(), max_length=16)
    visibility: UiVisibility = UiVisibility()

    @model_validator(mode="after")
    def validate_personal_options(self) -> "UiHomeWidget":
        identifiers = [field.id for field in self.configuration]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("widget configuration fields must have unique identifiers")
        if any(field.secret or field.type == UiFieldType.PASSWORD for field in self.configuration):
            raise ValueError("personal widget configuration cannot contain secrets")
        return self


class UiPlacement(ContractModel):
    """A visible header and up to three nested folders, never a permission path."""

    group: str = Field(default="Extensions", min_length=1, max_length=64)
    folders: tuple[Annotated[str, Field(min_length=1, max_length=64)], ...] = Field(
        default=(), max_length=3
    )

    @field_validator("group")
    @classmethod
    def visible_group(cls, value: str) -> str:
        if not value.strip() or any(ord(character) < 32 for character in value):
            raise ValueError("Placement group must contain a visible label")
        return value.strip()

    @field_validator("folders")
    @classmethod
    def visible_folders(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        result = tuple(value.strip() for value in values)
        if any(
            not value or value in {".", ".."} or "/" in value or "\\" in value
            or any(ord(character) < 32 for character in value)
            for value in result
        ):
            raise ValueError("Folders must contain visible individual labels")
        return result


class UiNavigationContribution(UiPlacement):
    """A first-class host navigation entry with one host-validated target."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    location: UiNavigationLocation
    label: str = Field(min_length=1, max_length=64)
    page_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    route_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    settings_section_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    action_id: str | None = Field(
        default=None, min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$"
    )
    icon: str | None = Field(default=None, min_length=1, max_length=64)
    order: int = Field(default=0, ge=-1_000, le=1_000)
    area: Literal["account", "preferences", "administration"] | None = None
    visibility: UiVisibility = UiVisibility()

    @model_validator(mode="after")
    def require_one_target(self) -> "UiNavigationContribution":
        targets = (self.page_id, self.route_id, self.settings_section_id, self.action_id)
        if sum(value is not None for value in targets) != 1:
            raise ValueError("navigation contribution must target exactly one destination")
        if self.area is not None and self.location is not UiNavigationLocation.SETTINGS_SIDEBAR:
            raise ValueError("Navigation area is only available in settings.sidebar")
        if self.area == "administration" and not self.visibility.admin_only:
            raise ValueError("Administration settings require administrator-only visibility")
        return self


class UiSettingsContribution(UiPlacement):
    """A plugin-provided Settings section, separate from plugin configuration."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=64)
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    icon: str | None = Field(default=None, min_length=1, max_length=64)
    order: int = Field(default=0, ge=-1_000, le=1_000)
    area: Literal["account", "preferences", "administration"] | None = None
    visibility: UiVisibility = UiVisibility()

    @model_validator(mode="after")
    def require_administrator_visibility(self) -> "UiSettingsContribution":
        if self.area == "administration" and not self.visibility.admin_only:
            raise ValueError("Administration settings require administrator-only visibility")
        return self


class UiOverlayContribution(ContractModel):
    """A host-level overlay rendered from a declared plugin page."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    order: int = Field(default=0, ge=-1_000, le=1_000)


class UiDialogContribution(ContractModel):
    """A host-level dialog backed by an existing declarative dialog."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    dialog_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")


class UiContextualAction(ContractModel):
    """An action exposed only in a declared game or media context."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    location: UiContextLocation
    label: str = Field(min_length=1, max_length=64)
    action_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    icon: str | None = Field(default=None, min_length=1, max_length=64)
    order: int = Field(default=0, ge=-1_000, le=1_000)


class UiPluginRoute(ContractModel):
    """A plugin-owned route under the host-controlled plugin route namespace."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    path: str = Field(min_length=1, max_length=255, pattern=r"^[a-z0-9][a-z0-9/_-]*$")
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")


class UiDocumentReader(ContractModel):
    """A scoped reader offered for game document rows, never arbitrary URLs."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=64)
    extensions: tuple[str, ...] = Field(default=("*",), min_length=1, max_length=64)
    order: int = Field(default=0, ge=-1_000, le=1_000)

    @field_validator("extensions")
    @classmethod
    def valid_extensions(cls, extensions: tuple[str, ...]) -> tuple[str, ...]:
        if any(not re.fullmatch(r"\*|\.[a-z0-9]{1,16}", value) for value in extensions):
            raise ValueError("document reader extensions must be lowercase suffixes or *")
        return extensions


class UiPageReplacement(ContractModel):
    """A page-specific replacement with no replace-any-page escape hatch."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    page: HostPage
    page_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    order: int = Field(default=0, ge=-1_000, le=1_000)


ThemeColor = Annotated[str, Field(pattern=r"^#[0-9a-fA-F]{6}$")]


class UiThemeColors(ContractModel):
    """Semantic color roles, never arbitrary stylesheets or executable assets."""

    background: ThemeColor
    surface: ThemeColor
    surface_alt: ThemeColor
    text: ThemeColor
    muted: ThemeColor
    accent: ThemeColor
    success: ThemeColor
    warning: ThemeColor
    error: ThemeColor
    info: ThemeColor
    purple: ThemeColor


class UiThemePalette(ContractModel):
    """A theme supplies both modes so System can follow the device."""

    light: UiThemeColors
    dark: UiThemeColors


class UiTheme(ContractModel):
    """A named optional palette offered to each account in Appearance."""

    id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    label: str = Field(min_length=1, max_length=128)
    description: str = Field(default="", max_length=512)
    colors: UiThemePalette
    order: int = 0


class PluginUiDocument(ContractModel):
    """Complete versioned UI document consumed by the native frontend host."""

    schema_version: UiSchemaVersion = UiSchemaVersion.V1
    api_contract_version: str = "1.0.0"
    plugin_id: str = Field(min_length=1, max_length=128, pattern=r"^[a-z0-9][a-z0-9._-]*$")
    title: str = Field(min_length=1, max_length=256)
    frontend: PluginFrontendDeclaration | None = None
    native_frontend: PluginNativeFrontendDeclaration | None = None
    settings: tuple[UiSettingsSection, ...] = ()
    actions: tuple[UiAction, ...] = ()
    tables: tuple[UiTable, ...] = ()
    dialogs: tuple[UiDialog, ...] = ()
    menus: tuple[UiMenuItem, ...] = ()
    pages: tuple[UiPage, ...] = ()
    extensions: tuple[UiExtension, ...] = ()
    home_widgets: tuple[UiHomeWidget, ...] = Field(default=(), max_length=32)
    themes: tuple[UiTheme, ...] = Field(default=(), max_length=32)
    navigation: tuple[UiNavigationContribution, ...] = ()
    settings_sections: tuple[UiSettingsContribution, ...] = ()
    overlays: tuple[UiOverlayContribution, ...] = ()
    dialog_contributions: tuple[UiDialogContribution, ...] = ()
    contextual_actions: tuple[UiContextualAction, ...] = ()
    routes: tuple[UiPluginRoute, ...] = ()
    page_replacements: tuple[UiPageReplacement, ...] = ()
    document_readers: tuple[UiDocumentReader, ...] = ()

    @field_validator("api_contract_version")
    @classmethod
    def validate_contract_version(cls, value: str) -> str:
        """Keep the minor UI/API boundary independent of the schema's wire major."""
        parse_semver(value)
        return value

    @model_validator(mode="after")
    def validate_references(self) -> "PluginUiDocument":
        def unique(values: list[str], kind: str) -> None:
            if len(values) != len(set(values)):
                raise ValueError(f"duplicate {kind} identifiers")

        setting_ids = [item.id for item in self.settings]
        action_ids = [item.id for item in self.actions]
        table_ids = [item.id for item in self.tables]
        dialog_ids = [item.id for item in self.dialogs]
        page_ids = [item.id for item in self.pages]
        extension_ids = [item.id for item in self.extensions]
        unique(setting_ids, "setting")
        unique(action_ids, "action")
        unique(table_ids, "table")
        unique(dialog_ids, "dialog")
        unique(page_ids, "page")
        unique(extension_ids, "extension")
        unique([item.id for item in self.home_widgets], "Home widget")
        unique([item.id for item in self.themes], "theme")
        home_extension_ids = {
            item.id for item in self.extensions if item.slot == HostExtensionSlot.HOME_AFTER_WIDGETS
        }
        if any(item.id in home_extension_ids for item in self.home_widgets):
            raise ValueError("Home widget identifiers cannot collide with Home extensions")
        unique([item.id for item in self.navigation], "navigation contribution")
        unique([item.id for item in self.settings_sections], "settings contribution")
        unique([item.id for item in self.overlays], "overlay contribution")
        unique([item.id for item in self.dialog_contributions], "dialog contribution")
        unique([item.id for item in self.contextual_actions], "contextual action")
        unique([item.id for item in self.routes], "plugin route")
        unique([item.path.strip("/") for item in self.routes], "plugin route path")
        for route in self.routes:
            if any(part == "" for part in route.path.split("/")):
                raise ValueError("plugin route path cannot contain empty segments")
            if route.path in page_ids and route.page_id != route.path:
                raise ValueError("plugin route path conflicts with a page identifier")
        unique([item.id for item in self.page_replacements], "page replacement")
        unique([item.id for item in self.document_readers], "document reader")

        action_set = set(action_ids)
        table_set = set(table_ids)
        dialog_set = set(dialog_ids)
        setting_set = set(setting_ids)
        page_set = set(page_ids)
        for menu in self.menus:
            if menu.page_id is not None and menu.page_id not in page_set:
                raise ValueError(f"menu references unknown page: {menu.page_id}")
            if menu.action_id is not None and menu.action_id not in action_set:
                raise ValueError(f"menu references unknown action: {menu.action_id}")
        for page in self.pages:
            if any(value not in setting_set for value in page.settings):
                raise ValueError(f"page {page.id} references an unknown setting")
            if any(value not in action_set for value in page.actions):
                raise ValueError(f"page {page.id} references an unknown action")
            if any(value not in table_set for value in page.tables):
                raise ValueError(f"page {page.id} references an unknown table")
            if any(value not in dialog_set for value in page.dialogs):
                raise ValueError(f"page {page.id} references an unknown dialog")
        for extension in self.extensions:
            if extension.page_id not in page_set:
                raise ValueError(f"extension {extension.id} references an unknown page")

        def require_page(contribution_id: str, page_id: str) -> None:
            if page_id not in page_set:
                raise ValueError(f"contribution {contribution_id} references an unknown page")

        for widget in self.home_widgets:
            require_page(widget.id, widget.page_id)
            if widget.mobile_page_id is not None:
                require_page(widget.id, widget.mobile_page_id)

        route_set = {item.id for item in self.routes}
        settings_contribution_set = {item.id for item in self.settings_sections}
        for navigation in self.navigation:
            if navigation.page_id is not None:
                require_page(navigation.id, navigation.page_id)
            if navigation.route_id is not None and navigation.route_id not in route_set:
                raise ValueError(f"navigation {navigation.id} references an unknown plugin route")
            if (
                navigation.settings_section_id is not None
                and navigation.settings_section_id not in settings_contribution_set
            ):
                raise ValueError(
                    f"navigation {navigation.id} references an unknown Settings section"
                )
            if navigation.action_id is not None and navigation.action_id not in action_set:
                raise ValueError(f"navigation {navigation.id} references an unknown action")
        for settings_section in self.settings_sections:
            require_page(settings_section.id, settings_section.page_id)
        for overlay in self.overlays:
            require_page(overlay.id, overlay.page_id)
        for route in self.routes:
            require_page(route.id, route.page_id)
        for replacement in self.page_replacements:
            require_page(replacement.id, replacement.page_id)
        for reader in self.document_readers:
            require_page(reader.id, reader.page_id)
        for dialog_contribution in self.dialog_contributions:
            if dialog_contribution.dialog_id not in dialog_set:
                raise ValueError(
                    f"dialog contribution {dialog_contribution.id} references an unknown dialog"
                )
        for contextual_action in self.contextual_actions:
            if contextual_action.action_id not in action_set:
                raise ValueError(
                    f"contextual action {contextual_action.id} references an unknown action"
                )
        return self
