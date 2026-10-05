"""Joining core headers requires separate area-wide permission grants."""

import pytest
from pydantic import ValidationError

from src.plugin_api.capabilities import capability_implies
from src.plugin_api.contracts import Capability, PluginUiDocument, UiNavigationContribution
from src.plugin_api.ui_permissions import filter_ui_document


def document(**contributions):
    return PluginUiDocument.model_validate({
        "plugin_id": "example.placement", "title": "Placement",
        "pages": [{"id": "page", "title": "Page"}], **contributions,
    })


def test_sidebar_permission_covers_all_headers_and_nested_folders():
    source = document(navigation=[{
        "id": name, "location": "main.sidebar", "label": name, "page_id": "page",
        "group": group, "folders": folders,
    } for name, group, folders in [
        ("games", "Your library", ["Games", "Challenges"]),
        ("media", "Your library", ["Media", "Jellyfin"]),
        ("tracking", "Keep track", ["Reports", "History", "Details"]),
    ]])
    ordinary = frozenset({"frontend.navigation.main", "frontend.navigation"})
    denied = filter_ui_document(source, ordinary)
    assert {item.group for item in denied.navigation} == {"Extensions"}
    assert denied.navigation[0].folders == ("Games", "Challenges")
    granted = filter_ui_document(source, ordinary | {"frontend.placement.sidebar"})
    assert [item.group for item in granted.navigation] == ["Your library", "Your library", "Keep track"]
    assert granted.navigation[2].folders == ("Reports", "History", "Details")


@pytest.mark.parametrize("area,group,permission", [
    ("account", "Account", "frontend.placement.settings.account"),
    ("preferences", "Library", "frontend.placement.settings.preferences"),
    ("administration", "Server management", "frontend.placement.settings.admin"),
])
def test_settings_placement_is_scoped_to_its_area(area, group, permission):
    item = {"id": "placed", "label": "Placed", "page_id": "page", "area": area,
            "group": group, "folders": ["Services", "Advanced"],
            "visibility": {"admin_only": area == "administration"}}
    source = document(settings_sections=[item], navigation=[{
        **item, "location": "settings.sidebar",
    }])
    ordinary = frozenset({"frontend.settings", "frontend.navigation.settings"})
    for other in ("frontend.placement.sidebar", "frontend.placement.settings.account",
                  "frontend.placement.settings.preferences", "frontend.placement.settings.admin"):
        filtered = filter_ui_document(source, ordinary | {other})
        expected = group if other == permission else "Extensions"
        assert filtered.settings_sections[0].group == expected
        assert filtered.navigation[0].group == expected
        assert filtered.settings_sections[0].folders == ("Services", "Advanced")


def test_custom_headers_and_folders_do_not_need_core_placement_permission():
    source = document(settings_sections=[{
        "id": "custom", "label": "Custom", "page_id": "page",
        "group": "My extension", "folders": ["Tools"],
    }])
    filtered = filter_ui_document(source, frozenset({"frontend.settings"}))
    assert filtered.settings_sections[0].group == "My extension"


def test_ordinary_navigation_and_full_api_do_not_imply_core_placement():
    for permission in (Capability.FRONTEND_PLACEMENT_SIDEBAR, Capability.FRONTEND_PLACEMENT_ADMIN,
                       Capability.FRONTEND_PLACEMENT_ACCOUNT, Capability.FRONTEND_PLACEMENT_PREFERENCES):
        assert not capability_implies(Capability.FRONTEND_NAVIGATION, permission)
        assert not capability_implies(Capability.FRONTEND_SETTINGS, permission)
        assert not capability_implies(Capability.FULL_API, permission)
        assert capability_implies(permission, permission)


@pytest.mark.parametrize("folders", [[""], [" "], [".."], ["a/b"], ["a\\b"], ["a", "b", "c", "d"]])
def test_folders_are_bounded_visible_labels(folders):
    with pytest.raises(ValidationError):
        UiNavigationContribution(id="entry", label="Entry", location="main.sidebar", page_id="page", folders=folders)


def test_admin_settings_navigation_requires_admin_visibility():
    with pytest.raises(ValidationError):
        UiNavigationContribution(id="entry", label="Entry", location="settings.sidebar",
                                 page_id="page", area="administration")
