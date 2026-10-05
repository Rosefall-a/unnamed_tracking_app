"""Bindings use the existing account store and a bounded portable key grammar."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.preferences import load_preferences, save_preferences, validate_preference
from src.helpers.shortcut_keys import normalize_shortcut_key
from src.main import app  # noqa: F401 - register ORM models


@pytest.mark.parametrize(
    "value",
    [
        None,
        [],
        {"bad/key": {}},
        {"nav.g": {"enabled": "false"}},
        {"nav.g": {"enabled_order": True}},
        {"nav.g": {"enabled_order": -1}},
        {"nav.g": {"enabled_order": 1.5}},
        {"nav.g": {"enabled_order": 9_007_199_254_740_992}},
        {"nav.g": {"keys": []}},
        {"nav.g": {"keys": ["Ctrl+Ctrl+K"]}},
        {"nav.g": {"keys": ["<script>"]}},
        {"nav.g": {"handler": "eval"}},
        {"nav.g": {"keys": ["A", "B", "C", "D", "E"]}},
        {f"nav.{index}": {} for index in range(513)},
    ],
)
def test_invalid_overrides_are_rejected(value):
    with pytest.raises(ValueError):
        validate_preference("keyboard_shortcut_overrides", value)


@pytest.mark.parametrize("value", ["false", 0, None])
def test_master_switch_requires_boolean(value):
    with pytest.raises(ValueError):
        validate_preference("keyboard_shortcuts_enabled", value)


@pytest.mark.asyncio
async def test_shortcut_changes_are_personal_and_keep_unavailable_plugin_choices():
    user_id = uuid4()
    row = SimpleNamespace(data={"ui_theme": "dark"})
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    overrides = {
        "nav.g": {"keys": ["shift + alt + g"], "enabled_order": 32},
        "plugin:example.removed:action": {
            "enabled": False,
            "keys": ["CtrlOrMeta+K"],
            "enabled_order": 31,
        },
    }
    result = await save_preferences(
        db, user_id, {"keyboard_shortcuts_enabled": False, "keyboard_shortcut_overrides": overrides}
    )
    assert result["ui_theme"] == "dark"
    assert result["keyboard_shortcut_overrides"]["nav.g"]["keys"] == ["Alt+Shift+G"]
    assert result["keyboard_shortcut_overrides"]["nav.g"]["enabled_order"] == 32
    reloaded = await load_preferences(db, user_id)
    assert reloaded["keyboard_shortcut_overrides"] == result["keyboard_shortcut_overrides"]
    assert (
        result["keyboard_shortcut_overrides"]["plugin:example.removed:action"]["enabled"] is False
    )
    assert user_id in db.scalar.call_args.args[0].compile().params.values()
    other = await load_preferences(SimpleNamespace(scalar=AsyncMock(return_value=None)), uuid4())
    assert other["keyboard_shortcuts_enabled"] is True
    assert other["keyboard_shortcut_overrides"] == {}


@pytest.mark.parametrize(
    "value, expected",
    [
        ("ctrlormeta+k", "CtrlOrMeta+K"),
        ("?", "?"),
        ("ArrowDown", "ArrowDown"),
        ("shift+alt+g", "Alt+Shift+G"),
    ],
)
def test_key_grammar_normalizes(value, expected):
    assert normalize_shortcut_key(value) == expected
