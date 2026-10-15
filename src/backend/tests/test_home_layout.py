"""The Home layout preference is checked for shape, not for which widgets exist."""

import pytest

from src.core.preferences import DEFAULTS, validate_preference


def _layout(**widget):
    base = {"id": "w1", "type": "rail", "x": 0, "y": 0, "w": 6, "h": 4, "settings": {}}
    return {
        "version": 1,
        "pages": [{"id": "home", "name": "Home", "options": {}, "widgets": [{**base, **widget}]}],
    }


def test_no_layout_by_default():
    assert DEFAULTS["home_layout"] is None
    assert validate_preference("home_layout", None) is None


def test_a_valid_layout_is_kept():
    clean = validate_preference("home_layout", _layout(settings={"count": 10}, variant="banner"))
    widget = clean["pages"][0]["widgets"][0]
    assert widget["settings"] == {"count": 10}
    assert widget["variant"] == "banner"


def test_an_unknown_widget_type_is_kept_not_rejected():
    clean = validate_preference("home_layout", _layout(type="from-a-removed-plugin"))
    assert clean["pages"][0]["widgets"][0]["type"] == "from-a-removed-plugin"


@pytest.mark.parametrize(
    "widget",
    [{"x": 12}, {"x": -1}, {"w": 0}, {"w": 13}, {"h": 0}, {"y": 1000}, {"id": ""}, {"type": 5}],
)
def test_bad_placement_is_rejected(widget):
    with pytest.raises(ValueError):
        validate_preference("home_layout", _layout(**widget))


def test_duplicate_ids_and_empty_pages_are_rejected():
    twice = _layout()
    twice["pages"][0]["widgets"].append(dict(twice["pages"][0]["widgets"][0]))
    with pytest.raises(ValueError):
        validate_preference("home_layout", twice)
    with pytest.raises(ValueError):
        validate_preference("home_layout", {"version": 1, "pages": []})


def test_an_oversized_layout_is_rejected():
    with pytest.raises(ValueError):
        validate_preference("home_layout", _layout(settings={"note": "x" * 70_000}))


def test_theme_colours_are_checked():
    assert validate_preference("theme_colors", {}) == {}
    assert validate_preference("theme_colors", {"accent": "#D68A34"}) == {"accent": "#d68a34"}
    for bad in ({"accent": "orange"}, {"accent": "#fff"}, {"glow": "#ffffff"}, "x", {"text": 5}):
        with pytest.raises(ValueError):
            validate_preference("theme_colors", bad)


def test_auto_collections_choice():
    assert DEFAULTS["collections_auto"] == "tab"
    for ok in ("tab", "mixed", "hidden"):
        assert validate_preference("collections_auto", ok) == ok
    with pytest.raises(ValueError):
        validate_preference("collections_auto", "somewhere")
