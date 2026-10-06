"""Custom account palettes accept color data, never arbitrary stylesheet content."""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.core.preferences import load_preferences, save_preferences, validate_preference


def palette():
    colors = {
        role: "#aABBcc"
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
    return {"light": dict(colors), "dark": dict(colors)}


@pytest.mark.parametrize("value", ["blue", {}, None, 1])
def test_unknown_palette_is_rejected(value):
    with pytest.raises(ValueError):
        validate_preference("ui_palette", value)


@pytest.mark.parametrize("value", [None, [], {"light": {}}, {"light": {}, "dark": {}}])
def test_incomplete_custom_palette_is_rejected(value):
    with pytest.raises(ValueError):
        validate_preference("ui_custom_palette", value)


@pytest.mark.parametrize(
    "color", ["red", "#fff", "url(https://example.invalid)", "#ffffff; color:red", "#ffffffff", 1]
)
def test_custom_palette_rejects_css_and_non_color_data(color):
    colors = palette()
    colors["light"]["accent"] = color
    with pytest.raises(ValueError):
        validate_preference("ui_custom_palette", colors)


@pytest.mark.asyncio
async def test_palette_is_normalized_and_persisted_only_for_its_account():
    account = uuid4()
    row = SimpleNamespace(data={"ui_theme": "system", "home_widgets": ["goals"]})
    db = SimpleNamespace(scalar=AsyncMock(return_value=row), commit=AsyncMock())
    result = await save_preferences(
        db, account, {"ui_palette": "custom", "ui_custom_palette": palette()}
    )
    assert result["ui_custom_palette"]["light"]["accent"] == "#aabbcc"
    assert result["ui_theme"] == "system"
    assert result["home_widgets"] == ["goals"]
    assert account in db.scalar.call_args.args[0].compile().params.values()
    other = SimpleNamespace(scalar=AsyncMock(return_value=None))
    defaults = await load_preferences(other, uuid4())
    assert defaults["ui_palette"] == "orange"
    assert defaults["ui_custom_palette"] == {}
    reset = await save_preferences(db, account, {"ui_palette": "orange", "ui_custom_palette": {}})
    assert reset["ui_custom_palette"] == {}
