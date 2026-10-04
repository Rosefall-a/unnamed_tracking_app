"""Validation coverage for host-owned plugin navigation and extension slots."""

import pytest
from pydantic import ValidationError

from src.api.routes.plugins import _filter_ui_document
from src.plugin_api.contracts import Capability, PluginUiDocument


def document_data() -> dict:
    return {
        "schema_version": "v1",
        "plugin_id": "example.extension",
        "title": "Example extension",
        "pages": [
            {
                "id": "dashboard",
                "title": "Dashboard",
                "navigation": {
                    "sidebar": True,
                    "label": "Example",
                    "order": 10,
                },
            }
        ],
        "extensions": [
            {
                "id": "home-summary",
                "slot": "home.after-widgets",
                "page_id": "dashboard",
                "order": 5,
            }
        ],
    }


def test_home_widgets_require_their_own_grant_and_retain_mobile_configuration():
    data = document_data()
    data["api_contract_version"] = "1.1.0"
    data["pages"].append({"id": "phone", "title": "Phone summary"})
    data["home_widgets"] = [
        {
            "id": "progress",
            "title": "Progress",
            "page_id": "dashboard",
            "mobile_page_id": "phone",
            "configuration": [{"id": "limit", "label": "Items", "type": "number", "default": 3}],
        }
    ]
    document = PluginUiDocument.model_validate(data)
    assert _filter_ui_document(document, frozenset({"frontend.page.extend"})).home_widgets == ()
    granted = _filter_ui_document(document, frozenset({"frontend.home.widgets"}))
    assert granted.home_widgets[0].mobile_page_id == "phone"
    assert granted.home_widgets[0].configuration[0].default == 3
    assert granted.extensions == ()


@pytest.mark.parametrize(
    "widget",
    [
        {"id": "progress", "title": "Progress", "page_id": "missing"},
        {
            "id": "progress",
            "title": "Progress",
            "page_id": "dashboard",
            "mobile_page_id": "missing",
        },
        {
            "id": "progress",
            "title": "Progress",
            "page_id": "dashboard",
            "configuration": [{"id": "token", "label": "Token", "type": "password"}],
        },
        {
            "id": "progress",
            "title": "Progress",
            "page_id": "dashboard",
            "configuration": [{"id": "token", "label": "Token", "type": "text", "secret": True}],
        },
    ],
)
def test_home_widgets_reject_invalid_pages_and_account_secrets(widget):
    data = document_data()
    data["api_contract_version"] = "1.1.0"
    data["home_widgets"] = [widget]
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)


def test_home_widgets_do_not_collide_with_existing_home_extension_identity():
    data = document_data()
    data["api_contract_version"] = "1.1.0"
    data["home_widgets"] = [{"id": "home-summary", "title": "Summary", "page_id": "dashboard"}]
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)


def test_ui_document_accepts_allowlisted_navigation_and_extension_slots() -> None:
    document = PluginUiDocument.model_validate(document_data())

    assert document.pages[0].navigation is not None
    assert document.pages[0].navigation.sidebar
    assert document.extensions[0].slot.value == "home.after-widgets"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slot", "game.detail.replace-header"),
        ("page_id", "missing"),
    ],
)
def test_ui_document_rejects_unknown_slots_and_pages(field: str, value: str) -> None:
    data = document_data()
    data["extensions"][0][field] = value

    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)


def test_sandboxed_frontend_can_coexist_with_declarative_host_contributions() -> None:
    data = document_data()
    data["frontend"] = {"entry": "frontend/index.html"}

    document = PluginUiDocument.model_validate(data)

    assert document.frontend is not None
    assert document.extensions[0].slot.value == "home.after-widgets"


def test_page_replacements_are_page_scoped_and_reference_declared_pages() -> None:
    data = document_data()
    data["page_replacements"] = [
        {"id": "replace-home", "page": "home", "page_id": "dashboard", "order": 1}
    ]
    document = PluginUiDocument.model_validate(data)

    assert document.page_replacements[0].page.value == "home"

    data["page_replacements"][0]["page"] = "everything"
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)


def test_native_and_host_contributions_are_filtered_by_effective_grants() -> None:
    data = document_data()
    data.update(
        {
            "frontend": {"entry": "frontend/index.html"},
            "native_frontend": {
                "entry": "native/index.js",
                "styles": ["native/style.css"],
            },
            "settings_sections": [
                {
                    "id": "sessions",
                    "label": "Sessions",
                    "page_id": "dashboard",
                }
            ],
            "overlays": [{"id": "help", "page_id": "dashboard"}],
        }
    )
    document = PluginUiDocument.model_validate(data)

    sandbox_only = _filter_ui_document(document, frozenset())
    assert sandbox_only.frontend is not None
    assert sandbox_only.native_frontend is None
    assert sandbox_only.extensions == ()
    assert sandbox_only.settings_sections == ()
    assert sandbox_only.overlays == ()

    privileged = _filter_ui_document(
        document,
        frozenset(
            {
                Capability.FRONTEND_NATIVE.value,
                Capability.FRONTEND_PAGE_EXTEND.value,
                Capability.FRONTEND_SETTINGS.value,
                Capability.FRONTEND_OVERLAY.value,
            }
        ),
    )
    assert privileged.native_frontend is not None
    assert privileged.extensions[0].id == "home-summary"
    assert privileged.settings_sections[0].id == "sessions"
    assert privileged.overlays[0].id == "help"


def test_navigation_targets_are_explicit_and_reference_declared_contributions() -> None:
    data = document_data()
    data["routes"] = [{"id": "sessions-route", "path": "sessions", "page_id": "dashboard"}]
    data["navigation"] = [
        {
            "id": "sessions-nav",
            "location": "main.sidebar",
            "label": "Sessions",
            "route_id": "sessions-route",
        }
    ]
    assert PluginUiDocument.model_validate(data).navigation[0].route_id == "sessions-route"

    data["navigation"][0]["page_id"] = "dashboard"
    with pytest.raises(ValidationError, match="exactly one"):
        PluginUiDocument.model_validate(data)


def theme_data():
    colors = {
        role: "#123456"
        for role in (
            "background",
            "surface",
            "surface_alt",
            "text",
            "muted",
            "accent",
            "success",
            "warning",
            "error",
            "info",
            "purple",
        )
    }
    return {
        "id": "blue-hour",
        "label": "Blue Hour",
        "colors": {
            "light": dict(colors),
            "dark": dict(colors),
        },
    }


def test_theme_registration_requires_its_own_low_risk_grant():
    from src.plugin_api.capabilities import capability_definition

    data = document_data()
    data["themes"] = [theme_data()]
    document = PluginUiDocument.model_validate(data)
    assert (
        _filter_ui_document(document, frozenset({"frontend.page.extend", "frontend.native"})).themes
        == ()
    )
    assert len(_filter_ui_document(document, frozenset({"frontend.themes"})).themes) == 1
    definition = capability_definition(Capability.FRONTEND_THEMES)
    assert definition.risk.value == "low"
    assert not definition.highly_privileged


@pytest.mark.parametrize(
    "invalid", ["red", "#fff", "url(https://invalid.test)", "#000000;display:none", None]
)
def test_theme_colors_cannot_inject_css(invalid):
    data = document_data()
    theme = theme_data()
    theme["colors"]["light"]["accent"] = invalid
    data["themes"] = [theme]
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)


def test_themes_require_both_modes_and_unique_ids():
    data = document_data()
    theme = theme_data()
    data["themes"] = [theme, theme]
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)
    del theme["colors"]["dark"]
    data["themes"] = [theme]
    with pytest.raises(ValidationError):
        PluginUiDocument.model_validate(data)
