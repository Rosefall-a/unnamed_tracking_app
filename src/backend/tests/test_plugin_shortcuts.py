"""Shortcut metadata cannot grant routes/actions or cross the old contract boundary."""

import pytest
from pydantic import ValidationError

from src.plugin_api.contracts import PluginUiDocument
from src.plugin_api.ui_permissions import filter_ui_document


def document(**changes):
    return PluginUiDocument.model_validate(
        {
            "api_contract_version": "1.1.0",
            "plugin_id": "example.shortcuts",
            "title": "Shortcuts",
            "pages": [{"id": "demo", "title": "Demo"}],
            "routes": [{"id": "demo", "path": "demo", "page_id": "demo"}],
            "shortcuts": [
                {"id": "open", "label": "Open demo", "keys": ["alt+q"], "route_id": "demo"}
            ],
            **changes,
        }
    )


def test_shortcuts_require_the_permission_and_the_target_route_permission():
    original = document()
    assert original.shortcuts[0].keys == ("Alt+Q",)
    assert not filter_ui_document(original, frozenset()).shortcuts
    assert not filter_ui_document(original, frozenset({"frontend.shortcuts"})).shortcuts
    assert not filter_ui_document(original, frozenset({"frontend.routes"})).shortcuts
    assert (
        filter_ui_document(original, frozenset({"frontend.routes", "frontend.shortcuts"})).shortcuts
        == original.shortcuts
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"api_contract_version": "1.0.0"},
        {"shortcuts": [{"id": "bad", "label": "Bad", "keys": ["N"], "page_id": "missing"}]},
        {"shortcuts": [{"id": "bad", "label": "Bad", "keys": ["N"], "action_id": "missing"}]},
        {
            "shortcuts": [
                {
                    "id": "bad",
                    "label": "Bad",
                    "keys": ["N"],
                    "when_route_id": "missing",
                    "route_id": "demo",
                }
            ]
        },
        {"shortcuts": [{"id": "bad", "label": "Bad", "keys": ["N"], "control": "create"}]},
        {
            "shortcuts": [
                {"id": "bad", "label": "Bad", "keys": ["N"], "page_id": "demo", "route_id": "demo"}
            ]
        },
        {"shortcuts": [{"id": "bad", "label": "Bad", "keys": ["Ctrl+Ctrl+K"], "route_id": "demo"}]},
    ],
)
def test_invalid_or_legacy_contributions_are_rejected(changes):
    with pytest.raises(ValidationError):
        document(**changes)


def test_action_shortcuts_do_not_bypass_the_action_capability():
    original = document(
        actions=[
            {
                "id": "notify",
                "label": "Notify",
                "handler": "plugin:notify",
                "capability": {"name": "notifications.send", "version": 1},
            }
        ],
        shortcuts=[
            {"id": "notify", "label": "Notify", "keys": ["Alt+Shift+N"], "action_id": "notify"}
        ],
    )
    assert not filter_ui_document(original, frozenset({"frontend.shortcuts"})).shortcuts
    assert filter_ui_document(
        original, frozenset({"frontend.shortcuts", "notifications.send"})
    ).shortcuts
