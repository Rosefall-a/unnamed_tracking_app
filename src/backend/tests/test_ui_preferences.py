"""Appearance and Home preferences use the existing per-user validation boundary."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.preferences import load_preferences, save_preferences, validate_preference


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("ui_theme", "sepia"),
        ("ui_theme", {"theme": "dark"}),
        ("ui_density", "tiny"),
        ("ui_style", "pocket"),  # Preserved concept is not yet an implemented style.
        ("ui_reduce_motion", "false"),
        ("ui_high_contrast", 1),
    ],
)
def test_unsupported_ui_preferences_are_rejected(key, value):
    with pytest.raises(ValueError):
        validate_preference(key, value)


@pytest.mark.asyncio
async def test_appearance_uses_account_store_and_preserves_other_preferences():
    user_id = uuid4()
    row = SimpleNamespace(data={"title_language": "native"})
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    result = await save_preferences(db, user_id, {"ui_theme": "dark", "ui_reduce_motion": True})
    assert row.data == {"title_language": "native", "ui_theme": "dark", "ui_reduce_motion": True}
    assert result["title_language"] == "native"
    assert result["ui_density"] == "comfortable"
    assert user_id in db.scalar.call_args.args[0].compile().params.values()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_absent_account_gets_ui_defaults_not_another_accounts_overrides():
    db = SimpleNamespace(scalar=AsyncMock(return_value=None))
    result = await load_preferences(db, uuid4())
    assert result["ui_theme"] == "system"
    assert result["ui_style"] == "archive-pocket"
    assert result["home_widgets"] == []


@pytest.mark.parametrize("value", [None, "goals", [1], ["goals", "goals"], ["unknown"],
                                       ["collection:"], ["plugin:demo:<script>"],
                                       ["collection:" + "x" * 512], ["goals"] * 33])
def test_invalid_home_widget_selections_are_rejected(value):
    with pytest.raises(ValueError):
        validate_preference("home_widgets", value)


@pytest.mark.asyncio
async def test_home_order_is_personal_and_keeps_unavailable_plugin_identifiers():
    user_id = uuid4()
    row = SimpleNamespace(data={"ui_theme": "dark", "calendar_week_start": 1})
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    selection = ["collection:Long Weekend", "plugin:disabled-plugin:progress", "goals"]
    result = await save_preferences(db, user_id, {"home_widgets": selection})
    assert result["home_widgets"] == selection
    assert result["ui_theme"] == "dark"
    assert result["calendar_week_start"] == 1
    assert user_id in db.scalar.call_args.args[0].compile().params.values()
    empty = await save_preferences(db, user_id, {"home_widgets": []})
    assert empty["home_widgets"] == []
