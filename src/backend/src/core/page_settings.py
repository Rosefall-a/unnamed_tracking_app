"""What a game's page shows. The same shape is used twice: as the defaults for
every game (a per-user preference, see core/preferences.py) and as one game's
overrides (Game.page_settings), where only the things that differ are stored.
"""

from __future__ import annotations

from typing import Any

# tabs that can be switched off; Overview is always there
OPTIONAL_TABS: tuple[str, ...] = (
    "Achievements",
    "Screenshots",
    "Clips",
    "Soundtrack",
    "Saves",
    "Docs",
    "Notes",
    "Stats",
)
# show: always. hide: never. auto: only once the game has something in it.
TAB_MODES: tuple[str, ...] = ("show", "hide", "auto")
DEFAULT_TAB_CHOICES: tuple[str, ...] = ("Overview", *OPTIONAL_TABS)

# each of these hides one thing on the page when true
HIDE_FLAGS: tuple[str, ...] = (
    "hide_rating",
    "hide_collections",
    "hide_favorite",
    "hide_credits",
    "hide_date_badge",
    "hide_platform_badge",
    "hide_history",
)

DEFAULT_PAGE_SETTINGS: dict[str, Any] = {
    "tabs": {tab: "show" for tab in OPTIONAL_TABS},
    "default_tab": "Overview",
    **{flag: False for flag in HIDE_FLAGS},
}


def validate_page_settings(value: Any, *, partial: bool) -> dict[str, Any]:
    """Check a page settings object. `partial` is a game's overrides, where any
    key may be missing; otherwise it is a full set of defaults and missing keys
    are filled in."""
    if not isinstance(value, dict):
        raise ValueError("page settings must be an object")
    unknown = set(value) - set(DEFAULT_PAGE_SETTINGS)
    if unknown:
        raise ValueError(f"Unknown page setting(s): {sorted(unknown)}")
    clean: dict[str, Any] = {}
    if "tabs" in value:
        tabs = value["tabs"]
        if not isinstance(tabs, dict):
            raise ValueError("tabs must be an object")
        bad = set(tabs) - set(OPTIONAL_TABS)
        if bad:
            raise ValueError(f"These tabs cannot be changed: {sorted(bad)}")
        if any(mode not in TAB_MODES for mode in tabs.values()):
            raise ValueError(f"A tab must be one of {list(TAB_MODES)}")
        clean["tabs"] = dict(tabs)
    if "default_tab" in value:
        if value["default_tab"] not in DEFAULT_TAB_CHOICES:
            raise ValueError(f"default_tab must be one of {list(DEFAULT_TAB_CHOICES)}")
        clean["default_tab"] = value["default_tab"]
    for flag in HIDE_FLAGS:
        if flag in value:
            if not isinstance(value[flag], bool):
                raise ValueError(f"{flag} must be true or false")
            clean[flag] = value[flag]
    if partial:
        return clean
    merged = {**DEFAULT_PAGE_SETTINGS, **clean}
    merged["tabs"] = {**DEFAULT_PAGE_SETTINGS["tabs"], **clean.get("tabs", {})}
    return merged
